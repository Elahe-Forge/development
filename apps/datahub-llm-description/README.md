SETUP
===

Download and install locally Ollama https://ollama.com/
Make sure to download the model used https://ollama.com/library/llama3

```bash
# example
ollama pull llama3
```


```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env # adjust any ENV with your tokens
```

RUN
===

```bash
python main.py # by default it will just write into the output folder
# change to ACRYL_WRITE="True" to write back into Acryl
```
