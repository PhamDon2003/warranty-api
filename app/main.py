from fastapi import FastAPI

app = FastAPI(
    title="Warranty API",
    description="API quản lý vòng đời serial và bảo hành thiết bị",
    version="1.0.0",
)


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}

