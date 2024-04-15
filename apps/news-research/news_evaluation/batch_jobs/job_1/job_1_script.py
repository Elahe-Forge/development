
import json
import os
import boto3
import nltk
from bert_score import score
from rouge import Rouge
from sentence_transformers import SentenceTransformer, util
from transformers import RobertaModel, RobertaTokenizer
from nltk.translate.bleu_score import sentence_bleu
from nltk.translate.meteor_score import single_meteor_score
import torch
from selfcheckgpt.modeling_mqag import MQAG
import logging
import datetime
import uuid
import pandas as pd
from botocore.exceptions import ClientError
import io

nltk.download('punkt')
nltk.download('wordnet')

logger = logging.getLogger()
logger.setLevel(logging.INFO)




def write_data_to_database(s3_bucket, news_metrics):
    s3_client = boto3.client('s3')
    if len(news_metrics) > 0:
        for record in news_metrics:
            try:
                issuer_name = record['issuer'].replace(" ", "_").lower()  # Replace spaces with underscores and convert to lowercase
                timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")  
                unique_id = uuid.uuid4()  # Generate a unique identifier to ensure uniqueness
                
                df = pd.DataFrame([record])
                parquet_buffer = io.BytesIO()
                df.to_parquet(parquet_buffer, index=False)

                s3_object_key = f'news-articles/{issuer_name}/news_record_{timestamp}_{unique_id}.parquet'
                s3_client.put_object(Bucket=s3_bucket, Key=s3_object_key, Body=parquet_buffer.getvalue())
                
                logger.info(f"Persisted record for issuer '{issuer_name}' to S3 bucket '{s3_bucket}' with key '{s3_object_key}'")
            except ClientError as e:
                logger.error(f"Failed to persist record for issuer '{issuer_name}' to S3 bucket '{s3_bucket}': {e}")
            except Exception as e:
                logger.error(f"Unexpected error occurred while persisting record for issuer '{issuer_name}': {e}")
    else:
        logger.info("No records to persist")
        




def calculate_metrics(reference, hypothesis):
    metrics = {}

    try:
        # Tokenize for BLEU
        reference_tokens = nltk.word_tokenize(reference)
        hypothesis_tokens = nltk.word_tokenize(hypothesis)

        # Calculate BLEU score
        bleu_score = sentence_bleu([reference_tokens], hypothesis_tokens)
        metrics["BLEU"] = bleu_score

    except Exception as e:
        print(f"Error calculating BLEU score: {e}")
        metrics["BLEU"] = None

    try:
        # Calculate METEOR score
        meteor_score_value = single_meteor_score(reference_tokens, hypothesis_tokens)
        metrics["METEOR"] = meteor_score_value

    except Exception as e:
        print(f"Error calculating METEOR score: {e}")
        metrics["METEOR"] = None

    try:
        # Calculate BERTScore
        P, R, F1 = score([hypothesis], [reference], lang='en', verbose=True)
        bert_score = F1.mean().item()
        metrics["BERT_score"] = bert_score

    except Exception as e:
        print(f"Error calculating BERTScore: {e}")
        metrics["BERT_score"] = None

    try:
        # Calculate ROUGE scores
        rouge = Rouge()
        rouge_scores = rouge.get_scores(hypothesis, reference, avg=True)
        metrics["ROUGE"] = rouge_scores

    except Exception as e:
        print(f"Error calculating ROUGE scores: {e}")
        metrics["ROUGE"] = None

    try:
        # Function to get embeddings from RoBERTa
        def get_roberta_embedding(text):
            encoded_input = tokenizer(text, return_tensors='pt', padding=True, truncation=True, max_length=512)
            with torch.no_grad():
                model_output = roberta_model(**encoded_input)
            return model_output.last_hidden_state.mean(dim=1)

        # Calculate Semantic Similarity using MiniLM
        st_model = SentenceTransformer('all-MiniLM-L6-v2')
        reference_embedding_minilm = st_model.encode(reference, convert_to_tensor=True)
        hypothesis_embedding_minilm = st_model.encode(hypothesis, convert_to_tensor=True)
        semantic_similarity_minilm = util.pytorch_cos_sim(reference_embedding_minilm, hypothesis_embedding_minilm).item()
        metrics["Semantic_similarity_minilm"] = semantic_similarity_minilm

    except Exception as e:
        print(f"Error calculating Semantic Similarity using MiniLM: {e}")
        metrics["Semantic_similarity_minilm"] = None

    try:
        # Calculate RoBERTa score
        tokenizer = RobertaTokenizer.from_pretrained('roberta-base')
        roberta_model = RobertaModel.from_pretrained('roberta-base')
        reference_embedding_roberta = get_roberta_embedding(reference)
        hypothesis_embedding_roberta = get_roberta_embedding(hypothesis)
        roberta_score = util.pytorch_cos_sim(reference_embedding_roberta, hypothesis_embedding_roberta).item()
        metrics["RoBERTa"] = roberta_score

    except Exception as e:
        print(f"Error calculating RoBERTa score: {e}")
        metrics["RoBERTa"] = None

    try:
        # Calculate MQAG
        torch.manual_seed(28)
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        mqag_model = MQAG(
            g1_model_type='race',  # race (more abstractive), squad (more extractive)
            device=device
        )
        mqag_score = mqag_model.score(candidate=hypothesis, reference=reference, num_questions=3, verbose=True)
        metrics["KL-divergence"] = mqag_score['kl_div']
        metrics["Hellinger"] = mqag_score['hellinger']
        metrics["Total-variation"] = mqag_score['total_variation']

    except Exception as e:
        print(f"Error calculating MQAG: {e}")
        metrics["KL-divergence"] = None
        metrics["Hellinger"] = None
        metrics["Total-variation"] = None

    return metrics



if __name__ == "__main__":
    
    s3_bucket = os.environ.get("BUCKET_NAME")
    input_data = os.environ.get('INPUT_DATA')


    # input_data = json.loads(os.environ.get('INPUT_DATA'))

    logger.info(f"input_data: {input_data}")

    # news_metrics = calculate_metrics(input_data['reference'], input_data['hypothesis'])
    
    # write_data_to_database(s3_bucket, news_metrics)

    # logger.info(f"news_metrics: {news_metrics}")
    

