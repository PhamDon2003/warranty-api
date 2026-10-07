from fastapi import FastAPI
from app.routers import auth, customers, dealers, products, serials, warranty

app = FastAPI(
    title="Warranty API",
    description="API quản lý vòng đời serial và bảo hành thiết bị",
    version="1.0.0",
)

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(dealers.router)
app.include_router(customers.router)
app.include_router(serials.router)
app.include_router(warranty.router)


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
