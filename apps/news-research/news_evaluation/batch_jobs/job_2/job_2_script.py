
import json
import os
import boto3


# Evaluation prompt template 
EVALUATION_PROMPT_TEMPLATE = """
You will be given one summary written for an article. Your task is to rate the summary on one metric.
Your answer should only be an integer score between 1-5. Do not provide any explanation and text.
Please make sure you read and understand these instructions very carefully. 
Please keep this document open while reviewing, and refer to it as needed.

Evaluation Criteria:

{criteria}

Evaluation Steps:

{steps}

Example:

Source Text:

{document}

Summary:

{summary}

Evaluation Form (scores ONLY):

- {metric_name}
"""

# Metric 1: Relevance

RELEVANCY_SCORE_CRITERIA = """
Relevance(1-5) - selection of important content from the source. \
The summary should include only important information from the source document. \
Annotators were instructed to penalize summaries which contained redundancies and excess information.
"""

RELEVANCY_SCORE_STEPS = """
1. Read the summary and the source document carefully.
2. Compare the summary to the source document and identify the main points of the article.
3. Assess how well the summary covers the main points of the article, and how much irrelevant or redundant information it contains.
4. Assign a relevance score from 1 to 5.
"""

# Metric 2: Coherence

COHERENCE_SCORE_CRITERIA = """
Coherence(1-5) - the collective quality of all sentences. \
We align this dimension with the DUC quality question of structure and coherence \
whereby "the summary should be well-structured and well-organized. \
The summary should not just be a heap of related information, but should build from sentence to a\
coherent body of information about a topic."
"""

COHERENCE_SCORE_STEPS = """
1. Read the article carefully and identify the main topic and key points.
2. Read the summary and compare it to the article. Check if the summary covers the main topic and key points of the article,
and if it presents them in a clear and logical order.
3. Assign a score for coherence on a scale of 1 to 5, where 1 is the lowest and 5 is the highest based on the Evaluation Criteria.
"""

# Metric 3: Consistency

CONSISTENCY_SCORE_CRITERIA = """
Consistency(1-5) - the factual alignment between the summary and the summarized source. \
A factually consistent summary contains only statements that are entailed by the source document. \
Annotators were also asked to penalize summaries that contained hallucinated facts.
"""

CONSISTENCY_SCORE_STEPS = """
1. Read the article carefully and identify the main facts and details it presents.
2. Read the summary and compare it to the article. Check if the summary contains any factual errors that are not supported by the article.
3. Assign a score for consistency based on the Evaluation Criteria.
"""

# Metric 4: Fluency

FLUENCY_SCORE_CRITERIA = """
Fluency(1-3): the quality of the summary in terms of grammar, spelling, punctuation, word choice, and sentence structure.
1: Poor. The summary has many errors that make it hard to understand or sound unnatural.
2: Fair. The summary has some errors that affect the clarity or smoothness of the text, but the main points are still comprehensible.
3: Good. The summary has few or no errors and is easy to read and follow.
"""

FLUENCY_SCORE_STEPS = """
Read the summary and evaluate its fluency based on the given criteria. Assign a fluency score from 1 to 3.
"""

llm_evaluation_metrics = {
    "Relevance": (RELEVANCY_SCORE_CRITERIA, RELEVANCY_SCORE_STEPS),
    "Coherence": (COHERENCE_SCORE_CRITERIA, COHERENCE_SCORE_STEPS),
    "Consistency": (CONSISTENCY_SCORE_CRITERIA, CONSISTENCY_SCORE_STEPS),
    "Fluency": (FLUENCY_SCORE_CRITERIA, FLUENCY_SCORE_STEPS),
}


def get_eval_score_gpt4(criteria: str, steps: str, document: str, summary: str, metric_name: str):
    try:
        llm_gpt4 = ChatOpenAI(model='gpt-4')
        human_message_prompt = HumanMessagePromptTemplate.from_template(EVALUATION_PROMPT_TEMPLATE)

        chat_prompt = ChatPromptTemplate.from_messages([human_message_prompt])

        chain = LLMChain(llm=llm_gpt4, prompt=chat_prompt)

        return chain.run(criteria=criteria,
            steps=steps,
            metric_name=metric_name,
            document=document,
            summary=summary)
    except Exception as e:
        print(e)
        return None

def get_eval_score_claude(criteria: str, steps: str, document: str, summary: str, metric_name: str):
    try:
    
        bedrock = boto3.client(service_name='bedrock-runtime',
                            region_name='us-west-2',
                            aws_access_key_id=aws_access_key,
                            aws_secret_access_key=aws_access_secret)
        
        prompt = EVALUATION_PROMPT_TEMPLATE.format(
            criteria=criteria,
            steps=steps,
            metric_name=metric_name,
            document=document,
            summary=summary,
        )

        body = json.dumps({
            "prompt": f"\n\nHuman:{prompt}\nraw text:{prompt}\n\nAssistant: I only provide an integer score between 1-5.",
            "max_tokens_to_sample": 2000,
            "temperature": 0.2,
            "top_p": 0.9,})


        modelId = 'anthropic.claude-v2'
        accept = 'application/json'
        contentType = 'application/json'

        response = bedrock.invoke_model(body=body, modelId=modelId, accept=accept, contentType=contentType)    
        response_body = json.loads(response.get('body').read())
        completion = response_body.get('completion')
        score_num = re.search(r'\d+', completion).group()


        return score_num
    except Exception as e:
        print(e)
        return None

def evaluate_summary(document, summary):
    
    evaluation_results = {}
    for metric_name, (criteria, steps) in llm_evaluation_metrics.items():
        score = get_eval_score_gpt4(criteria, steps, document, summary, metric_name)
        evaluation_results[metric_name] = score

        # evaluation_results["claude"]["claude_examiner_metrics"][metric_name] = get_eval_score_claude(criteria, steps, record["raw_text"], record["claude"]["summary"], eval_type)
        # evaluation_results["claude"]["gpt_examiner_metrics"][metric_name] = get_eval_score_gpt4(criteria, steps, record["raw_text"], record["claude"]["summary"], eval_type)   
        # evaluation_results["gpt"]["claude_examiner_metrics"][metric_name] = get_eval_score_claude(criteria, steps, record["raw_text"], record["gpt"]["summary"], eval_type)
        # evaluation_results["gpt"]["gpt_examiner_metrics"][metric_name] = get_eval_score_gpt4(criteria, steps, record["raw_text"], record["gpt"]["summary"], eval_type)
    return evaluation_results

def process_data(data):
    document = data['document']
    summary = data['summary']
    evaluation_results = evaluate_summary(document, summary)
    write_data_to_database(evaluation_results)
    return evaluation_results

def write_data_to_database(data):
    # Code to write the evaluation results back to the database
    pass

if __name__ == "__main__":
    # Read input data from environment variable or command-line argument
    input_data = json.loads(os.environ.get('INPUT_DATA'))

    # Evaluate the summary
    evaluation_results = process_data(input_data)

    # Output the evaluation results (for logging or further processing)
    print(json.dumps(evaluation_results))
