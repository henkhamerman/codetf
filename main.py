from transformers import RobertaTokenizer, T5ForConditionalGeneration, T5Tokenizer, AutoTokenizer, \
    AutoModelForSeq2SeqLM, Seq2SeqTrainingArguments, Seq2SeqTrainer, DataCollatorForSeq2Seq
import evaluate
from datasets import DatasetDict, Dataset
from tqdm import tqdm
import torch

checkpoint = 'Salesforce/codet5p-770m'  # ALT: Salesforce/codet5p-770m(-py) or Salesforce/codet5-small
tokenizer = AutoTokenizer.from_pretrained(checkpoint)
model = AutoModelForSeq2SeqLM.from_pretrained(checkpoint,
                                              torch_dtype=torch.float32,
                                              trust_remote_code=True)
prompt = "Refactor this Java method such that it is correct: \n"
bleu_metric = evaluate.load("bleu")
em_metric = evaluate.load("exact_match")


# adds prompt + tokenizes input
def preprocess(samples, prefix=""):
    model_inputs = tokenizer([prefix + sample for sample in samples["buggy"]], return_tensors="pt", padding=True, truncation=True)
    labels = tokenizer(text_target=samples["fix"], max_length=384, truncation=True)
    model_inputs["labels"] = labels["input_ids"]
    return model_inputs

# loading in files
with open("test-buggy.txt", "r") as file:
    buggy_data = file.readlines()[:3]

with open("test-fixed.txt", "r") as file:
    fixed_data = file.readlines()[:3]

# max_length_buggy = max([len(tokenizer(line)) for line in buggy_data])
# max_length_fixed = max([len(tokenizer(line)) for line in fixed_data])


data_dict = {
    "buggy": buggy_data,
    "fix": fixed_data
}

dataset = Dataset.from_dict(data_dict)  # create Hugging Face Dataset
dataset_dict = dataset.train_test_split(test_size=0.1)

tokenized_datasets = dataset_dict.map(preprocess, batched=True)  # convert the whole dataset into tokens at once


def compute_metrics(p):
    generated_code = tokenizer.batch_decode(p.predictions, skip_special_tokens=True)

    # BLEU and EM need references for evaluation
    references_bleu = [ref.strip() for ref in dataset_dict["test"]["fix"]]
    references_em = [ref.strip() for ref in dataset_dict["test"]["fix"]]

    # compute BLEU and EM scores using Hugging Face's Evaluate module
    bleu_score = bleu_metric.compute(predictions=generated_code, references=references_bleu)
    em_score = em_metric.compute(predictions=generated_code, references=references_em)

    return {"bleu_score": bleu_score, "em_score": em_score}


batch_size = 16
model_name = checkpoint.split("/")[-1]
args = Seq2SeqTrainingArguments(
    f"{model_name}-finetuned-bugs2fix",
    evaluation_strategy="epoch",
    learning_rate=2e-5,
    per_device_train_batch_size=batch_size,
    per_device_eval_batch_size=batch_size,
    weight_decay=0.01,
    save_total_limit=3,
    num_train_epochs=1,
    predict_with_generate=True,
    fp16=False,  # set to True if GPU supports Mixed Precision training
    push_to_hub=False,
)

data_collator = DataCollatorForSeq2Seq(tokenizer, model=model)

trainer = Seq2SeqTrainer(
    model,
    args,
    train_dataset=tokenized_datasets["train"],
    eval_dataset=tokenized_datasets["test"],
    data_collator=data_collator,
    tokenizer=tokenizer,
    compute_metrics=compute_metrics
)

trainer.train()

# for epoch in range(int(args.num_train_epochs)):
#     epoch_iterator = tqdm(trainer.get_train_dataloader(), desc=f"Epoch {epoch}")
#
#     for step, inputs in enumerate(epoch_iterator):
#         trainer.train()
#         epoch_iterator.set_postfix(samples_processed=(step + 1) * args.per_device_train_batch_size)
#
# # Final evaluation after fine-tuning

final_eval_metrics = trainer.evaluate()
print("Final Evaluation Metrics:")
for key, value in final_eval_metrics.items():
    if isinstance(value, dict):
        for subkey, subvalue in value.items():
            print(f"{key}_{subkey} = {subvalue}")
    else:
        print(f"{key} = {value}")
