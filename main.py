from sklearn.metrics import accuracy_score, precision_recall_fscore_support
import numpy as np
from transformers import RobertaTokenizer, T5ForConditionalGeneration, T5Tokenizer, AutoTokenizer, \
    AutoModelForSeq2SeqLM, Seq2SeqTrainingArguments, Seq2SeqTrainer, DataCollatorForSeq2Seq, AutoConfig, \
    DataCollatorWithPadding, TrainingArguments, Trainer, AutoModelForSequenceClassification
import evaluate
from datasets import DatasetDict, Dataset, concatenate_datasets
import torch
import os

unique_refactoring_types = ["Extract Method", "Inline Method", "Rename Package", "Move Method", "Move Class", "Move Attribute", "Pull Up Method",
                            "Pull Up Attribute", "Push Down Method", "Push Down Attribute", "Extract Interface", "Extract Superclass"]  # 12
label2id = {label: i for i, label in enumerate(unique_refactoring_types)}
id2label = {i: label for i, label in enumerate(unique_refactoring_types)}

checkpoint = 'Salesforce/codet5-small'  # ALT: Salesforce/codet5p-770m(-py), a larger model
tokenizer = AutoTokenizer.from_pretrained(checkpoint)
model = AutoModelForSequenceClassification.from_pretrained(checkpoint,
                                              torch_dtype=torch.float32,
                                              trust_remote_code=True,
                                              num_labels=len(unique_refactoring_types),
                                              id2label=id2label,
                                              label2id=label2id,)

print(f"Model Size: {sum(p.numel() for p in model.parameters())/1000000} million parameters")
accuracy = evaluate.load("accuracy")
prompt = ""


# computes the length of the longest tokenized source code file
def compute_max_length():
    max_input_length = 0
    for code in examples["code"]:
        tokens = tokenizer(code, truncation=True, max_length=10000)
        max_input_length = max(max_input_length, len(tokens['input_ids']))
    return max_input_length


# adds prompt if needed + tokenizes input
def preprocess(samples, prefix=""):
    max_input_length = compute_max_length()
    input_tokenized = tokenizer(
        [prefix + sample for sample in samples["code"]],
        return_tensors="pt",
        truncation=True,
        padding="max_length",
        max_length=max_input_length,
    )

    model_inputs = {
        "input_ids": input_tokenized["input_ids"],
        "attention_mask": input_tokenized["attention_mask"],
        "labels": torch.tensor(samples["labels"], dtype=torch.long),
    }

    return model_inputs


# adjustable parameters
LOC = 100
fine_tune = False


# loading in files
data_dir = 'preprocess/data'
examples = {"labels": [], "code": []}
file_count = 0


# read the files in a dictionary
def read_files(dir, dataset):
    global file_count
    for filename in os.listdir(data_dir):
        if filename.endswith(".md"):
            filepath = os.path.join(dir, filename)

            with open(filepath, "r", encoding="utf-8") as file:
                lines = file.readlines()
                if not LOC >= len(lines) > 3:
                    pass
                    # print(f"Skipping empty/big file: {filepath}")
                else:
                    labels_line = lines[0].strip()
                    labels = eval(labels_line.split(":")[1].strip())

                    code = "".join(lines[1:])
                    dataset["labels"].append(label2id[labels[0]])  # uses first label
                    dataset["code"].append(code)
                    file_count += 1
    print(f"Used {file_count} files for fine-tuning/evaluation")
    return dataset


# create Hugging Face Dataset
examples = read_files(data_dir, examples)
dataset = Dataset.from_dict(examples)
dataset_dict = dataset.train_test_split(test_size=0.3)

tokenized_datasets = dataset_dict.map(preprocess, batched=True)  # convert the whole dataset into tokens at once


# will only be used at evaluation, takes an EvalPrediction and returns a dict{string:metric}
def compute_metrics(p):
    predictions = np.argmax(p.predictions[0], axis=1)
    true_labels = p.label_ids

    # accuracy, weighted precision, weighted recall, weighted F1-score
    accuracy = accuracy_score(true_labels, predictions)
    precision, recall, f1, _ = precision_recall_fscore_support(true_labels, predictions, average='weighted', zero_division=0)

    print("Predicted Labels:", predictions)
    print("True Labels:", true_labels)

    print(f"Accuracy: {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall: {recall:.4f}")
    print(f"F1-score: {f1:.4f}")

    return {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1,
    }


def main(finetune):
    batch_size = 1
    model_name = checkpoint.split("/")[-1]
    args = TrainingArguments(
        f"{model_name}-finetuned-bugs2fix",
        evaluation_strategy="epoch",
        learning_rate=2e-5,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        gradient_accumulation_steps=1,
        weight_decay=0.01,
        save_total_limit=3,
        num_train_epochs=1,
        fp16=False,  # set to True if GPU supports Mixed Precision training
        push_to_hub=False,
    )

    data_collator = DataCollatorWithPadding(tokenizer)

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=tokenized_datasets["train"],
        eval_dataset=tokenized_datasets["test"],
        data_collator=data_collator,
        tokenizer=tokenizer,
        compute_metrics=compute_metrics,
    )

    if finetune:
        trainer.train()

    trainer.evaluate()


if __name__ == "__main__":
    main(finetune=fine_tune)  # set to False for evaluation only
