from codetf.models import load_model_pipeline, model_zoo
from codetf.trainer.codet5_trainer import CodeT5Seq2SeqTrainer
from codetf.data_utility.codexglue_dataset import CodeXGLUEDataset
from codetf.performance.evaluation_metric import EvaluationMetric
from codetf.data_utility.base_dataset import CustomDataset

code_generation_model = load_model_pipeline(model_name="codet5", task="refine",
                                            model_type="base", is_eval=True,
                                            load_in_8bit=False, load_in_4bit=False, weight_sharding=False)

result = code_generation_model.predict(["""
def factorial(n):
  if n == 0:
    return 1
  else:
    return n * factorial(n - 1)
"""])
print(result)


