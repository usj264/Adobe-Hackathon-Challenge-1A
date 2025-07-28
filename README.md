# PDF Outline Extractor (Advanced Version)

This is a Dockerized PDF outline extraction solution for Adobe India Hackathon 2025 Round 1A.

## 💡 Features
- Advanced heading classification using patterns and heuristics
- Title detection via metadata and content
- JSON output as per schema

## 🐳 Build Docker

```bash
docker build --platform=linux/amd64 -t pdf-processor .
```

## 🚀 Run Docker

```bash
docker run --rm -v $(pwd)/sample_dataset/pdfs:/app/input:ro -v $(pwd)/sample_dataset/outputs:/app/output --network none pdf-processor
```

## ✅ Requirements Met
- CPU-only (no GPU)
- Under 200MB model size (none used)
- Network disabled in container
