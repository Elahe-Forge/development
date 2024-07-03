import argparse
import logging
import os
import sys

import boto3
from datasets import load_from_disk
from sagemaker.experiments.run import load_run
from sagemaker.session import Session
from sklearn.metrics import accuracy_score, log_loss, precision_recall_fscore_support
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
)

if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    # Hyperparameters sent by the client are passed as command-line arguments to the script
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--train_batch_size", type=int, default=32)
    parser.add_argument("--eval_batch_size", type=int, default=32)
    parser.add_argument("--warmup_steps", type=int, default=500)
    parser.add_argument("--model_name", type=str)
    parser.add_argument("--learning_rate", type=str, default=5e-5)
    parser.add_argument("--weight_decay", type=str, default=0)

    parser.add_argument("--instance_type", type=str, default="ml.g4dn.xlarge")
    parser.add_argument("--instance_count", type=int, default=1)
    parser.add_argument("--train_input_path", type=str)
    parser.add_argument("--test_input_path", type=str)

    parser.add_argument("--job_name", type=str)
    parser.add_argument("--job_id", type=str)
    parser.add_argument("--output_path", type=str)
    parser.add_argument("--model_output_path", type=str)

    # Data, model, and output directories
    parser.add_argument(
        "--output_data_dir", type=str, default=os.environ["SM_OUTPUT_DATA_DIR"]
    )
    parser.add_argument("--model_dir", type=str, default=os.environ["SM_MODEL_DIR"])
    parser.add_argument("--n_gpus", type=str, default=os.environ["SM_NUM_GPUS"])
    parser.add_argument(
        "--training_dir", type=str, default=os.environ["SM_CHANNEL_TRAIN"]
    )
    parser.add_argument("--test_dir", type=str, default=os.environ["SM_CHANNEL_TEST"])
    parser.add_argument(
        "--region", type=str, default="us-west-2", help="SageMaker Region"
    )

    args, _ = parser.parse_known_args()

    # Set up logging
    logger = logging.getLogger(__name__)

    logging.basicConfig(
        level=logging.getLevelName("INFO"),
        handlers=[logging.StreamHandler(sys.stdout)],
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Load datasets
    train_dataset = load_from_disk(args.training_dir)
    test_dataset = load_from_disk(args.test_dir)

    tokenizer = AutoTokenizer.from_pretrained(args.model_name)

    # trying to add this to the script!
    # tokenizer helper function
    def tokenize(batch):
        return tokenizer(batch["text"], padding="max_length", truncation=True)

    # tokenize dataset
    train_dataset = train_dataset.map(tokenize, batched=True)
    test_dataset = test_dataset.map(tokenize, batched=True)

    # set format for pytorch
    train_dataset = train_dataset.rename_column("label", "labels")
    train_dataset.set_format("torch", columns=["input_ids", "attention_mask", "labels"])
    test_dataset = test_dataset.rename_column("label", "labels")
    test_dataset.set_format("torch", columns=["input_ids", "attention_mask", "labels"])

    logger.info(f"Loaded train_dataset length is: {len(train_dataset)}")
    logger.info(f"Loaded test_dataset length is: {len(test_dataset)}")

    # Compute metrics function for multi-class classification
    ## add precision and recall metrics later
    ### source: https://www.kaggle.com/code/nkitgupta/evaluation-metrics-for-multi-class-classification
    def compute_metrics(pred):
        labels = pred.label_ids
        preds = pred.predictions.argmax(-1)
        # precision, recall, f1, _ = precision_recall_fscore_support(
        #     labels, preds, average="binary"
        # )
        acc_score = accuracy_score(labels, preds)
        log_loss_score = log_loss(labels, pred.predictions)
        return {"acc": acc_score, "log_loss": log_loss_score}

    num_labels = int(max(train_dataset["labels"])) + 1
    # Download model from model hub
    model = AutoModelForSequenceClassification.from_pretrained(
        args.model_name, num_labels=num_labels
    )

    # Define training args
    training_args = TrainingArguments(
        output_dir=args.model_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.train_batch_size,
        per_device_eval_batch_size=args.eval_batch_size,
        warmup_steps=args.warmup_steps,
        weight_decay=float(args.weight_decay),
        evaluation_strategy="epoch",
        logging_strategy="epoch",
        logging_dir=f"{args.output_data_dir}/logs",
        learning_rate=float(args.learning_rate),
    )

    # Create Trainer instance
    trainer = Trainer(
        model=model,
        args=training_args,
        compute_metrics=compute_metrics,
        train_dataset=train_dataset,
        eval_dataset=test_dataset,
        tokenizer=tokenizer,
    )

    session = Session(boto3.session.Session(region_name=args.region))
    with load_run(sagemaker_session=session) as run:

        # logging parameters to SageMaker experiments
        run.log_parameters(
            {
                "num_train_samples": len(train_dataset),
                "num_test_samples": len(test_dataset),
                "epochs": args.epochs,
                "train_batch_size": args.train_batch_size,
                "eval_batch_size": args.eval_batch_size,
                "model_name": args.model_name,
                "job_id": args.job_id,
                "learning_rate": args.learning_rate,
                "weight_decay": args.weight_decay,
                "n_gpus": args.n_gpus,
                "instance_type": args.instance_type,
                "instance_count": args.instance_count,
            }
        )

        # Train model
        trainer.train()

        # Evaluate model
        eval_result = trainer.evaluate(eval_dataset=test_dataset)

        print("--trainer.state.log_history--")
        for obj in trainer.state.log_history:
            print(obj)
            if "eval_loss" in obj:
                run.log_metric(
                    name="eval:loss", value=obj["eval_loss"], step=int(obj["epoch"])
                )
                run.log_metric(
                    name="eval:accuracy", value=obj["eval_acc"], step=int(obj["epoch"])
                )
                run.log_metric(
                    name="eval:log_loss",
                    value=obj["eval_log_loss"],
                    step=int(obj["epoch"]),
                )

        print("--Eval result--")
        print(eval_result)

        run.log_metric(name="final:loss", value=eval_result["eval_loss"], step=0)
        run.log_metric(name="final:accuracy", value=eval_result["eval_acc"], step=0)
        run.log_metric(
            name="final:log_loss", value=eval_result["eval_log_loss"], step=0
        )

        # Write eval result to file which can be accessed later in S3 ouput
        with open(
            os.path.join(args.output_data_dir, "eval_results.txt"), "w"
        ) as writer:
            print(f"***** Eval results *****")
            print(eval_result)
            for key, value in sorted(eval_result.items()):
                writer.write(f"{key} = {value}\n")

        model_dir = os.environ["SM_MODEL_DIR"]

        # Save the model to s3
        print("model_dir", model_dir)
        trainer.save_model(model_dir)

        run.log_artifact(name="train", value=args.train_input_path, is_output=False)
        run.log_artifact(name="test", value=args.test_input_path, is_output=False)

        # print("trainer.model_data:", trainer.model_data)
        run.log_artifact(
            name="SageMaker.ModelArtifact",
            value=args.model_output_path,
        )
