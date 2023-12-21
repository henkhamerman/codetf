from transformers import RobertaTokenizer, T5ForConditionalGeneration, T5Tokenizer, AutoTokenizer, \
    AutoModelForSeq2SeqLM, Seq2SeqTrainingArguments, Seq2SeqTrainer, DataCollatorForSeq2Seq
import evaluate
from datasets import DatasetDict, Dataset
from tqdm import tqdm
import torch

checkpoint = 'Salesforce/codet5p-770m'  # Salesforce/codet5p-770m(-py)
tokenizer = AutoTokenizer.from_pretrained(checkpoint)  # 'Salesforce/codet5-small'
model = AutoModelForSeq2SeqLM.from_pretrained(checkpoint,
                                              torch_dtype=torch.float32,
                                              trust_remote_code=True)
prompt = "Refactor this Java method such that it is correct: \n"
bleu_metric = evaluate.load("bleu")
em_metric = evaluate.load("exact_match")


def preprocess(sample, prefix=""):
    model_input = tokenizer([prefix + sample["buggy"]], return_tensors="pt", padding=True, truncation=True)
    labels = tokenizer(text_target=sample["fix"], max_length=128, truncation=True)
    model_input["labels"] = labels["input_ids"]
    return model_input


with open("test-buggy.txt", "r") as file:
    buggy_data = file.readlines()[:3]

with open("test-fixed.txt", "r") as file:
    fixed_data = file.readlines()[:3]

data_dict = {  # Hugging Face Dataset
    "buggy": buggy_data,
    "fix": fixed_data
}
dataset = Dataset.from_dict(data_dict)
dataset_dict = dataset.train_test_split(test_size=0.1)

generated_code = []  # generated code for each example will be stored here

current_dataset = dataset_dict["test"]

for i, example in tqdm(enumerate(current_dataset["buggy"]), total=len(current_dataset["buggy"]), desc=f"Evaluating model on test set"):
    encoding = preprocess(example, prompt)
    out = model.generate(**encoding, max_new_tokens=150)
    generated_code_decoded = tokenizer.decode(out[0], skip_special_tokens=True)
    generated_code.append(generated_code_decoded)

# references for evaluation
references_bleu = [ref.strip() for ref in dataset_dict["test"]["fix"]]
references_em = [ref.strip() for ref in dataset_dict["test"]["fix"]]

# Compute BLEU and EM scores
bleu_results = bleu_metric.compute(predictions=[generated_code], references=[references_bleu])
em_results = em_metric.compute(predictions=generated_code, references=references_em)

print(f"BLEU score: {bleu_results}")
print(f"EM score: {em_results}")
