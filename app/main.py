from fastapi import FastAPI

app = FastAPI(title="Builder Operating System")


@app.get("/")
def read_root():
    return {"message": "Hello World"}
