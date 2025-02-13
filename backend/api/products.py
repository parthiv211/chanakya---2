#products.py
import gzip
import io
import json
import re
from datetime import datetime
from uuid import uuid4
import ast

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import delete, func, insert, select, update, desc

from api.helper import (
    check_if_role_exists,
    flatten_product,
    get_user_from_token,
    sql_to_pd,
    unflatten_product,
)
from config import logger
from model import db, ql
from model.db import get_session
from api.helper import add_tags_to_image_aws, handleTemporaryImages
from api.email_helper import send_email_status_update, send_email_reject_product, send_new_product_add_email

router = APIRouter(prefix="/products")


@router.post("/")
async def create_product(product: ql.CreateProduct, user=Depends(get_user_from_token)):
    """
    Input: Most of the product and size details
    Output: product id

    Products are created in a 'Design' state
    """
    #logger.info(f"Received payload: {product.dict()}")
    
    if not check_if_role_exists(
        user["department"]["roles"], "product design details", "create"
    ):
        raise HTTPException(
            403, "You don't have permission to create the design details of a product"
        )
    
    
    #  remove field productImages from product
    productImages=[]
    if "productImages" in product.dict():
        productImages = product.productImages
        del product.productImages

    logger.info(f"Received payload after removing productImages: {product.dict()}")

    if product.mrp or product.cost:
        logger.warning(
            f"{user['name']} doesnt have permission to create product mrp or cost, setting it to None"
        )
        product.mrp = None
        product.cost = None

    pattern = r"^\d{4}-.{0,13}$"
    if not re.match(pattern, product.style_id):
        raise HTTPException(
            400,
            "Style id should have 4 digits followed by a hyphen and 0-13 characters",
        )

    async with get_session() as s:
        query = select(db.Styles).where(
            db.Styles.style_id == product.style_id, db.Styles.deleted is not True
        )
        res = (await s.execute(query)).unique().all()
    if res:
        raise HTTPException(400, f"Style id {product.style_id} already exists")

    logger.info(f"{user['name']} is trying to create a product")
    product_id = str(uuid4())
    styles_row, sizes_rows = flatten_product(product, product_id)
    # cost_dict = {
    #     "cost": product.cost,
    #     "date": datetime.now(),
    #     "created_by": user["id"],
    # }
    styles_row.update(
        {
            "product_id": product_id,
            "created_by": user["id"],
            "updated_by": user["id"],
            "cost": product.cost,
            "product_description": product.product_description  # Add this line
        }
    )
    async with get_session() as s:
        query = insert(db.Styles).values(styles_row)
        await s.execute(query)
        query = insert(db.Sizes).values(sizes_rows)
        await s.execute(query)

        await send_new_product_add_email("Design", product.style_id, product_id, user["email"], datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    if productImages:
        urls = handleTemporaryImages(product_id, [], productImages)
    else:
        urls=[]
    if urls:
        logger.info(f"Temporary images saved successfully: {urls}")
        async with get_session() as s:
            query = (
                update(db.Styles)
                .where(db.Styles.product_id == product_id)
                .values({"images": str(urls)})
            )
            await s.execute(query)
            log_entry = db.ProductUpdateLog(
                user_id=user["id"],
                email=user["email"],
                product_id=product_id,
                timestamp=datetime.now(),
                changes_summary="Images upadted!"
            )
            s.add(log_entry)
    
        main_image_url = urls[0]
        if product.tags:
            tag_image_urls=[]
            async with get_session() as s:
                tag_names = product.tags
                normalized_tag_names = [tag_name.replace(" ", "").lower() for tag_name in tag_names]
                tag_url_query = select([db.Tag.tag_url_column]).where(db.Tag.tag_name.in_(normalized_tag_names))
                tag_url_result = await s.execute(tag_url_query)
                tag_url_rows = tag_url_result.fetchall()
                tag_image_urls = [row[0] for row in tag_url_rows]

            if not tag_image_urls and tag_image_urls != []:
                logger.error("Failed to fetch tag image URLs")
                raise HTTPException(status_code=403, detail="Failed to update and save the image")
            main_image_url = main_image_url.replace("%23", "#")
            output_path = add_tags_to_image_aws(product_id, main_image_url, tag_image_urls)
            if output_path:
                logger.info(f"Image updated with tags and saved to: {output_path}")
            else:
                logger.error("Failed to update and save the image.")
                raise HTTPException(status_code=403, detail="Failed to update and save the image.")
    
    return {
        "msg": "Product created successfully",
        "info": {"product_id": styles_row["product_id"]},
    }

'''
@router.put("/{product_id}")
async def edit_product(
    product_id: str, product: ql.EditProduct, user=Depends(get_user_from_token)
):
    """
    Input: product id, details to be changed

    Used to Edit, Approve, Delete a product
    """
    if not check_if_role_exists(
        user["department"]["roles"], "product design details", "update"
    ):
        raise HTTPException(
            403, "You don't have permission to edit the design details of a product"
        )
    if product.mrp:
        logger.warning(
            f"{user['name']} doesnt have permission to edit product mrp, setting it to None"
        )
        product.mrp = None
    if not check_if_role_exists(user["department"]["roles"], "product cost", "update"):
        if product.cost:
            logger.warning(
                f"{user['name']} doesnt have permission to edit product cost, setting them to None"
            )
            product.cost = None
    logger.info(
        f"{user['name']} is trying to edit a product with a change in {product}"
    )

    # deleting a product
    if product.deleted == True:
        if product.status == "Design":
            async with get_session() as s:
                query = delete(db.Styles).where(db.Styles.product_id == product_id)
                await s.execute(query)
            return {
                "msg": "Product permanently deleted successfully",
                "info": {"product_id": product_id},
            }
        else:
            async with get_session() as s:
                query = (
                    update(db.Styles)
                    .where(db.Styles.product_id == product_id)
                    .values({"deleted": True})
                )
                await s.execute(query)
            return {
                "msg": "Product soft deleted successfully",
                "info": {"product_id": product_id},
            }

    styles_row, sizes_rows = flatten_product(product, product_id)
    styles_row.update({"updated_at": datetime.now(), "updated_by": user["id"]})
    async with get_session() as s:
        query = (
            update(db.Styles)
            .where(db.Styles.product_id == product_id)
            .values(styles_row)
        )
        await s.execute(query)
        for size in sizes_rows:
            query = (
                update(db.Sizes)
                .where(db.Sizes.product_id == product_id)
                .where(db.Sizes.standard_size == size["standard_size"])
                .values(size)
            )
            await s.execute(query)
    return {
        "msg": "Product edited successfully",
        "info": {"product_id": product_id},
    }

'''

@router.put("/{product_id}")
async def edit_product(
    product_id: str,
    product: ql.EditProduct,
    user=Depends(get_user_from_token)
):
    """
    Input: product id, details to be changed
    Used to Edit, Approve, Delete a product
    """
    logger.info(f"Received payload: {product.dict()}")

    #  remove field productImages from product
    productImages=[]
    if "productImages" in product.dict():
        productImages = product.productImages
        del product.productImages

    logger.info(f"Received payload after removing productImages: {product.dict()}")

    if not check_if_role_exists(user["department"]["roles"], "product design details", "update"):
        raise HTTPException(403, "You don't have permission to edit the design details of a product")

    # if product.mrp:
    #     logger.warning(f"{user['name']} doesn't have permission to edit product mrp, setting it to None")
    #     product.mrp = None

    if not check_if_role_exists(user["department"]["roles"], "product cost", "update"):
        if product.cost:
            logger.warning(f"{user['name']} doesn't have permission to edit product cost, setting them to None")
            product.cost = None

    logger.info(f"{user['name']} is trying to edit a product with a change in {product}")

    old_values_dict = {}
    async with get_session() as s:
        query = select(db.Styles).where(db.Styles.product_id == product_id)
        result = await s.execute(query)
        old_values = result.scalars().first()

        if old_values:
            old_values_dict = {column.name: getattr(old_values, column.name) for column in db.Styles.__table__.columns}
        else:
            raise HTTPException(status_code=404, detail="Product not found")

    # deleting a product
    if product.deleted == True:
        async with get_session() as s:
            changes = ""
            if product.status == "Design":
                query = delete(db.Styles).where(db.Styles.product_id == product_id)
                changes = f"Product permanently deleted. Old values: {old_values_dict}"
                await s.execute(query)
                # return {
                #     "msg": "Product permanently deleted successfully",
                #     "info": {"product_id": product_id},
                # }
            else:
                query = (
                    update(db.Styles)
                    .where(db.Styles.product_id == product_id)
                    .values({"deleted": True})
                )
                changes = f"Product soft deleted. Old values: {old_values_dict}"
                await s.execute(query)
                # return {
                #     "msg": "Product soft deleted successfully",
                #     "info": {"product_id": product_id},
                # }
            log_entry = db.ProductUpdateLog(
                user_id=user["id"],
                email=user["email"],
                product_id=product_id,
                timestamp=datetime.now(),
                changes_summary=changes
            )
            s.add(log_entry)
        return {
            "msg": "Product deleted successfully",
            "info": {"product_id": product_id},
        }

    styles_row, sizes_rows = flatten_product(product, product_id)
    dateTimeNow = datetime.now()

    if product.hierarchy is None:
        # Ignore null values in styles_row if hierarchy is None
        styles_row = {k: v for k, v in styles_row.items() if v is not None}
    
    styles_row.update({
        "updated_at": dateTimeNow,
        "updated_by": user["id"],
        
    })

    logger.info(f"Updated styles_row: {styles_row}")

    async with get_session() as s:
        query = (
            update(db.Styles)
            .where(db.Styles.product_id == product_id)
            .values(styles_row)
        )
        await s.execute(query)

        if product.sizes and sizes_rows:
            query = delete(db.Sizes).where(db.Sizes.product_id == product_id)
            await s.execute(query)
            query = insert(db.Sizes).values(sizes_rows)
            await s.execute(query)
        
        # changes = f"Product updated. Old values: {old_values_dict}, New values: {styles_row}"
        # log_entry = db.ProductUpdateLog(
        #     user_id=user["id"],
        #     email=user["email"],
        #     product_id=product_id,
        #     timestamp=datetime.now(),
        #     changes_summary=changes
        # )
        # s.add(log_entry)
        changes_summary = []
        for key, new_value in styles_row.items():
            old_value = old_values_dict.get(key)
            if new_value != old_value and key != "updated_at" and key != "updated_by" and key != "created_at" and key != "created_by" and key != "product_id":
                changes_summary.append(f"Column '{key}' old value '{old_value}' is changed to new value '{new_value}'")

        # Create log entry
        changes = f"{' | '.join(changes_summary)}"
        log_entry = db.ProductUpdateLog(
            user_id=user["id"],
            email=user["email"],
            product_id=product_id,
            timestamp=dateTimeNow,
            changes_summary=changes
        )
        if changes!="":
            s.add(log_entry)
    
        if old_values_dict.get('status') != product.status:
            style_id_email = product.style_id if product.style_id else old_values_dict.get('style_id')
            await send_email_status_update(old_values_dict.get('status'), product.status, style_id_email, product_id, user["email"], dateTimeNow.strftime("%Y-%m-%d %H:%M:%S"))
    
    old_images_str = old_values_dict.get('images', '[]')
    logger.info(f"Old images string: {old_images_str}")

    try:
        # Convert string representation of list to an actual list
        old_images = ast.literal_eval(old_images_str)
        if not isinstance(old_images, list):
            raise ValueError("Images field is not a list")
    except (ValueError, SyntaxError) as e:
        logger.error(f"Error parsing images string: {e}")
        old_images = []

    # Check if temporary images have changed
    if productImages and productImages != old_images:
        urls = handleTemporaryImages(product_id, old_images, productImages)
    else:
        urls=[]
    if urls:
        logger.info(f"Temporary images saved successfully: {urls}")
        async with get_session() as s:
            query = (
                update(db.Styles)
                .where(db.Styles.product_id == product_id)
                .values({"images": str(urls)})
            )
            await s.execute(query)
            log_entry = db.ProductUpdateLog(
                user_id=user["id"],
                email=user["email"],
                product_id=product_id,
                timestamp=dateTimeNow,
                changes_summary="Images upadted!"
            )
            s.add(log_entry)
        old_images=urls

    if old_images:
        print(old_images, type(old_images))
        main_image_url = old_images[0]  # Get the first image URL from the array
        print(main_image_url)

        # Check if tags have changed
        if product.tags != old_values_dict.get('tags'):
            if main_image_url:
                tag_image_urls=[]
                async with get_session() as s:
                    print(product.tags)
                    tag_names = product.tags
                    normalized_tag_names = [tag_name.replace(" ", "").lower() for tag_name in tag_names]
                    tag_url_query = select([db.Tag.tag_url_column]).where(db.Tag.tag_name.in_(normalized_tag_names))
                    tag_url_result = await s.execute(tag_url_query)
                    tag_url_rows = tag_url_result.fetchall()
                    tag_image_urls = [row[0] for row in tag_url_rows]

                if not tag_image_urls and tag_image_urls != []:
                    logger.error("Failed to fetch tag image URLs")
                    raise HTTPException(status_code=403, detail="Failed to update and save the image")
                main_image_url = main_image_url.replace("%23", "#")
                output_path = add_tags_to_image_aws(product_id, main_image_url, tag_image_urls)
                if output_path:
                    logger.info(f"Image updated with tags and saved to: {output_path}")
                else:
                    logger.error("Failed to update and save the image.")
                    raise HTTPException(status_code=403, detail="Failed to update and save the image.")

    return {
        "msg": "Product edited successfully",
        "info": {"product_id": product_id},
    }

@router.put("/reject/{product_id}")
async def reject_product(
    product_id: str, 
    product: ql.RejectProduct,
    user=Depends(get_user_from_token)
    ):
    """
    Input: product id
    Output: product id

    Used to reject a product
    """
    logger.info(f"Rejecting product with id: {product_id}")
    logger.info(f"Reject message: {product.dict()}")
    if not check_if_role_exists(user["department"]["roles"], "reject product", "update"):
        raise HTTPException(403, "You don't have permission to reject this product!")
    
    if not product.rejectMessage:
        raise HTTPException(403, "Reject message is required!")

    async with get_session() as s:
        existingDataQuery = select(db.Styles).where(db.Styles.product_id == product_id)
        existingData = (await s.execute(existingDataQuery)).unique().scalars().first()
        if not existingData:
            raise HTTPException(404, "Product not found!")

        existingDataStatus = existingData.status

        query = (
            update(db.Styles)
            .where(db.Styles.product_id == product_id)
            .values({
                "status": "Merchandise",
                "updated_at": datetime.now(),
                "updated_by": user["id"]
            })
        )
        await s.execute(query)
        log_entry = db.ProductUpdateLog(
            user_id=user["id"],
            email=user["email"],
            product_id=product_id,
            timestamp=datetime.now(),
            changes_summary=f"Product rejected! Reject message: {product.rejectMessage}"
        )
        s.add(log_entry)

        await send_email_reject_product(existingDataStatus, "Merchandise", existingData.style_id, product_id, user["email"], datetime.now().strftime("%Y-%m-%d %H:%M:%S"), product.rejectMessage)
    return {
        "msg": "Product rejected successfully",
        "info": {"product_id": product_id},
    }

@router.get("/{product_id}")
async def get_product_details(product_id: str, user=Depends(get_user_from_token)):
    """
    Input: product id
    Output: Complete product and size details
    """
    if not check_if_role_exists(
        user["department"]["roles"], "product design details", "read"
    ):
        raise HTTPException(
            403, "You don't have permission to read the design details of a product"
        )

    logger.info(
        f"{user['name']} is trying to fetch details for product id: {product_id}"
    )
    async with get_session() as s:
        query = select(db.Styles).where(db.Styles.product_id == product_id)
        style_row = (await s.execute(query)).unique().first()
    product = unflatten_product(style_row[0], style_row[0].sizes)
    product.product_description = style_row[0].product_description  # Add this line

    if not check_if_role_exists(user["department"]["roles"], "product mrp", "read"):
        product.mrp = None
    if not check_if_role_exists(user["department"]["roles"], "product cost", "read"):
        product.cost = None

    user_ids = {int(product.created_by), int(product.updated_by)}
    async with get_session() as s:
        query = select(db.User).where(db.User.id.in_(user_ids))
        res = (await s.execute(query)).unique().all()
        res = sql_to_pd(res)

    product.created_by = res[res["id"] == int(product.created_by)]["email"].values[0]
    product.updated_by = res[res["id"] == int(product.updated_by)]["email"].values[0]

    logs={}
    async with get_session() as s:
        query = (
            select(db.ProductUpdateLog)
            .where(db.ProductUpdateLog.product_id == product_id)
            .order_by(desc(db.ProductUpdateLog.timestamp))
        )
        logs = (await s.execute(query)).unique().all()

    # Convert logs to a list of dictionaries
    logs_list = [log._asdict() for log in logs]

    return {"msg": "Product fetched successfully", "info": product,  "logs": logs_list}


@router.get("/")
async def get_field_options(hierarchy: bool = False, user=Depends(get_user_from_token)):
    """
    Output:
        Allowed values for columns that have fixed options
        Colour family with the colours in it
        Hierarchy of the products with their available sizes and default measurements
    """
    logger.info(
        f"{user['name']} is trying to fetch the field options (hierarchy: {hierarchy})"
    )
    if hierarchy:
        result = {"field_options": {}}
        with open("static/fieldoptions.json", "r") as f:
            result["field_options"] = json.load(f)
        with open("static/hierarchy.csv", "r") as f:
            df = pd.read_csv(f)
            result["hierarchy_and_default_measurements"] = json.loads(
                df.to_json(orient="records")
            )
        byte_stream = io.BytesIO()
        with gzip.GzipFile(fileobj=byte_stream, mode="w") as fout:
            fout.write(json.dumps(result).encode("utf-8"))
        compressed_data = byte_stream.getvalue()

        return Response(compressed_data, media_type="bytes")
    else:
        async with get_session() as s:
            query = select([func.min(db.Styles.cost), func.max(db.Styles.cost)])
            cost_range = (await s.execute(query)).all()[0]
            query = select([func.min(db.Styles.mrp), func.max(db.Styles.mrp)])
            mrp_range = (await s.execute(query)).all()[0]
            query = select(db.Channel.name)
            channels = (await s.execute(query)).all()
            query = select(db.Styles.product).distinct()
            products = (await s.execute(query)).all()

        with open("static/colors.json", "r") as f:
            colors = json.load(f)
        with open("static/filters.json", "r") as f:
            filters = json.load(f)
        return {
            "msg": "Fetched data to initiate the app",
            "info": {
                "mrp": mrp_range,
                "cost": cost_range,
                "colors": colors,
                "filters": filters,
                "channels": [c[0] for c in channels],
                "products": sorted([p[0] for p in products]),
            },
        }
