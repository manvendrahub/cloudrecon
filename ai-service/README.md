# CloudRecon AI service (Python)

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --port 8000
```
Use Python 3.10 to 3.12. The first start downloads the LaMa model (about 200 MB), so it needs internet.
If `simple-lama-inpainting` cannot be installed, remove it from requirements.txt; the service then uses OpenCV inpainting.
Set `MAX_SIDE` (default 1024) to control the working resolution of the model.
