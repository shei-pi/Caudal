from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryRead, CategoryTree, CategoryUpdate
from app.services.seed import seed_categories

router = APIRouter(prefix="/api/categories", tags=["categories"])


def _build_tree(categories: list[Category]) -> list[CategoryTree]:
    by_id = {c.id: CategoryTree.model_validate(c) for c in categories}
    roots = []
    for cat in by_id.values():
        if cat.parent_id is None:
            roots.append(cat)
        else:
            parent = by_id.get(cat.parent_id)
            if parent:
                parent.children.append(cat)
    return roots


@router.get("", response_model=list[CategoryTree])
def list_categories_tree(db: Session = Depends(get_db)):
    cats = db.query(Category).order_by(Category.name).all()
    return _build_tree(cats)


@router.get("/flat", response_model=list[CategoryRead])
def list_categories_flat(db: Session = Depends(get_db)):
    return db.query(Category).order_by(Category.name).all()


@router.post("/seed", status_code=201)
def seed(db: Session = Depends(get_db)):
    count = seed_categories(db)
    return {"seeded": count}


@router.post("", response_model=CategoryRead, status_code=201)
def create_category(data: CategoryCreate, db: Session = Depends(get_db)):
    category = Category(**data.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.put("/{category_id}", response_model=CategoryRead)
def update_category(category_id: int, data: CategoryUpdate, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    if category.is_system:
        raise HTTPException(status_code=400, detail="Cannot modify system category")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=204)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    from app.models.transaction import Transaction

    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    if category.is_system:
        raise HTTPException(status_code=400, detail="Cannot delete system category")
    tx_count = db.query(Transaction).filter(Transaction.category_id == category_id).count()
    if tx_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Category has {tx_count} transactions. Reassign them first.",
        )
    db.delete(category)
    db.commit()
