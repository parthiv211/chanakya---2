#bulkupdate
import requests
from io import BytesIO
import asyncio
import boto3
from uuid import uuid4
from datetime import datetime
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select, update
import logging
import model.db as db
from model import ql
from api.helper import check_if_role_exists, get_user_from_token, upload_to_s3,add_tags_to_image
from config import settings, logger, send_notification, settings, s3_client
from model.db import get_session
import json
from api.email_helper import send_bulk_status_update_notification, send_email_status_update

router = APIRouter(prefix="/import")
# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


@router.put("/updateStatus/")
async def update_status(request: ql.BulkUpdateStatusRequest, user=Depends(get_user_from_token)):
    logger.info(f"Received bulk update status request: {request.json()}")

    # Check user permissions
    if not check_if_role_exists(user["department"]["roles"], "product status", "update"):
        raise HTTPException(status_code=403, detail="You don't have permission to update product status")

    # Assign variables from request
    product_ids = request.productIds
    new_status = request.newStatus
    
    error = "Product status failed to update"

    required_fields = {
        "Topwear": ["across_shoulder", "chest", "front_length"],
        "Bottomwear": ["garment_waist", "inseam_length"],
        "Coordinates": ["garment_waist", "inseam_length", "across_shoulder", "chest", "front_length"]
        # Add other types as necessary
    }

    # Use a session to interact with the database
    async with get_session() as session:
        # try:
            # Query Styles table
        query_styles = select(db.Styles.product_id, db.Styles.brick).where(
            db.Styles.product_id.in_(product_ids),
            db.Styles.status == "Design"
        )
        logger.info("Before executing query for styles")
        result_styles = await session.execute(query_styles)
        logger.info("After executing query for styles")
        
        # Map product IDs to their corresponding brick types
        product_bricks = {row.product_id: row.brick for row in result_styles}
        logger.info(f"Product bricks: {product_bricks}")

        if not product_bricks:
            error = "No products with status 'Design' found to update"
            raise HTTPException(status_code=404, detail="No products with status 'Design' found to update")

        # Group product IDs by their brick type
        grouped_product_ids = {}
        for product_id, brick in product_bricks.items():
            if brick not in grouped_product_ids:
                grouped_product_ids[brick] = set()
            grouped_product_ids[brick].add(product_id)

        # Process each brick type
        valid_product_ids = set()
        for brick_type, ids in grouped_product_ids.items():
            if brick_type not in required_fields:
                error = f"Unsupported brick type '{brick_type}'"
                raise HTTPException(status_code=400, detail=error)

            # Query Sizes table with dynamic field checks
            query_sizes = select(db.Sizes.product_id).where(
                db.Sizes.product_id.in_(list(ids)),
                *[getattr(db.Sizes, field).isnot(None) for field in required_fields[brick_type]]
            )
            logger.info(f"Before executing query for sizes for brick type '{brick_type}'")
            result_sizes = await session.execute(query_sizes)
            logger.info(f"After executing query for sizes for brick type '{brick_type}'")
            valid_sizes_product_ids = {row.product_id for row in result_sizes}
            logger.info(f"Valid sizes product IDs for brick type '{brick_type}': {valid_sizes_product_ids}")

            # Intersect to get valid product IDs for this brick type
            valid_product_ids.update(valid_sizes_product_ids)

        if not valid_product_ids:
            error = "No products with status 'Design' and all required measurements found to update"
            raise HTTPException(status_code=404, detail="No products with status 'Design' and all required measurements found to update")

        # Update products with status "Design" to new status
        query_update = update(db.Styles).where(
            db.Styles.product_id.in_(list(valid_product_ids))
        ).values(status=new_status, updated_by=user["id"], updated_at=datetime.now())
        result_update = await session.execute(query_update)

        # Commit changes if rows were updated
        if result_update.rowcount == 0:
            error = "No products were updated"
            raise HTTPException(status_code=404, detail="No products were updated")
        else:
            for product_id in list(valid_product_ids):
                log_entry = db.ProductUpdateLog(
                    user_id=user["id"],
                    email=user["email"],
                    product_id=product_id,
                    timestamp=datetime.now(),
                    changes_summary=f"Column 'status' old value 'Design' is changed to new value '{new_status}'"
                )
                session.add(log_entry)
            
            style_ids = ""
            for product_id in list(valid_product_ids):
                existingDataQuery = select(db.Styles).where(db.Styles.product_id == product_id)
                result_styles = (await session.execute(existingDataQuery)).unique().scalars().first()
                style_ids += f"{result_styles.style_id}, "
            style_ids = style_ids[:-2]
            
            await send_bulk_status_update_notification("Design", new_status, style_ids, user["email"], datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        await session.commit()

        # except Exception as e:
        #     logger.error(f"Error during database operation: {str(e)}")
        #     await session.rollback()
        #     raise HTTPException(status_code=500, detail="Internal server error")
        return {"msg": "Product statuses updated successfully", "status": "success"}
    # return {"msg": "Product statused failed to update", "status": "failed"}
    # raise HTTPException(status_code=404, detail="Product status failed to update")
    raise HTTPException(status_code=404, detail=error)


@router.get("/")
async def get_templates(user=Depends(get_user_from_token)):
    logger.info(f"{user['name']} fetched upload templates")
    return {
        "msg": "Upload templates fetched",
        "info": {
            "bulk_update_ean_mrp_cost": {
                "file": "https://tigc-chanakya.s3.ap-south-1.amazonaws.com/csv/bulk_update_ean_mrp_cost.csv",
                "primary_key": ["product_id", "standard_size"],
            },
            "bulk_update_cost": {
                "file": "https://tigc-chanakya.s3.ap-south-1.amazonaws.com/csv/bulk_update_cost.csv",
                "primary_key": ["product_id"],
            },
            "bulk_update_ids": {
                "file": "https://tigc-chanakya.s3.ap-south-1.amazonaws.com/csv/bulk_update_ids.csv",
                "primary_key": ["ean"],
            },
            "bulk_update_dates": {
                "file": "https://tigc-chanakya.s3.ap-south-1.amazonaws.com/csv/bulk_update_dates.csv",
                "primary_key": ["product_id"],
            },
            "bulk_update_images": {
                "file": "https://tigc-chanakya.s3.ap-south-1.amazonaws.com/csv/bulk_update_images.csv",
                "primary_key": ["product_id"],
            },
        },
    }



async def upload_ean_mrp_cost(df, user_id, user_email):
    async with get_session() as s:
        query = select(db.Sizes.product_id, db.Sizes.standard_size, db.Sizes.ean).where(
            db.Sizes.product_id.in_(df["product_id"].unique())
        )
        query2 = select(db.Styles.mrp, db.Styles.cost).where(
            db.Styles.product_id.in_(df["product_id"].unique())
        )
        unique_eans = select(db.Sizes.ean)

        resp = await s.execute(query)
        resp2 = await s.execute(query2)
        unique_eans = (await s.execute(unique_eans)).unique().all()

    products = pd.DataFrame(resp)
    styles = pd.DataFrame(resp2)

    if products.empty or styles.empty:
        raise HTTPException(
            422, "No Products found with the given product_ids, check for spaces"
        )

    if not products.ean.isnull().all():
        raise HTTPException(422, "Some Products already have an ean")

    if not styles.mrp.isnull().all():
        raise HTTPException(422, "Some Products already have an mrp")

    if not styles.cost.isnull().all():
        raise HTTPException(422, "Some Products already have an cost")

    unique_eans = set([x[0] for x in unique_eans])
    if set.intersection(set(df.ean.unique()), unique_eans):
        raise HTTPException(422, "Some EANs already exist in the database")

    product_id_email = []
    product_update_log = {}

    async with get_session() as s:
        for _, row in df.iterrows():
            values = {"ean": int(row["ean"])}
            query = (
                update(db.Sizes)
                .where(db.Sizes.product_id == row["product_id"])
                .where(db.Sizes.standard_size == str(row["standard_size"]))
                .values(values)
            )
            await s.execute(query)
            values = {
                "status": "Catalog",
                "updated_by": int(user_id),
                "updated_at": datetime.now(),
            }
            if not pd.isnull(row["mrp"]):
                values["mrp"] = row["mrp"]
            if not pd.isnull(row["cost"]):
                values["cost"] = row["cost"]
            query = (
                update(db.Styles)
                .where(db.Styles.product_id == row["product_id"])
                .values(values)
            )
            await s.execute(query)

            product_id_email.append(row["product_id"])
            if row["product_id"] not in product_update_log:
                product_update_log[row["product_id"]] = {
                    "mrp": row["mrp"],
                    "cost": row["cost"],
                    "eans": {}
                }
            product_update_log[row["product_id"]]["eans"][row["standard_size"]] = row["ean"]
        
        if len(product_id_email) == len(df):
            for product_id in list(set(product_id_email)):
                dateTimeNow = datetime.now()
                style_id_email_query = await s.execute(select(db.Styles.style_id).where(db.Styles.product_id == product_id))
                style_id_email = style_id_email_query.scalar()
                await send_email_status_update("Merchandise", "Catalog", style_id_email, product_id, user_email, dateTimeNow.strftime("%Y-%m-%d %H:%M:%S"))
            
            async with get_session() as s:
                for product_id, data in product_update_log.items():
                    log_entry = db.ProductUpdateLog(
                        user_id=user_id,
                        email=user_email,
                        product_id=product_id,
                        timestamp=datetime.now(),
                        changes_summary = (
                            f"EANs Imported from CSV:\n"
                            f"{data['eans']}\n"
                            f"MRP and Cost updated with the values from CSV:\n"
                            f"  MRP: {data['mrp']}\n"
                            f"  Cost: {data['cost']}\n"
                            f"Also, product status updated from Merchandise to Catalog."
                        )
                    )
                    s.add(log_entry)
        else:
            raise HTTPException(422, "Something went wrong, Please try again")

async def update_cost(df, user_id, user_email):
    # Ensure that no cells are missing
    if df.isnull().any().any():
        raise HTTPException(status_code=422, detail="All columns must be filled")

    # Ensure Cost column contains only integers
    if not pd.api.types.is_numeric_dtype(df['cost']):
        raise HTTPException(status_code=422, detail="Cost must be an integer")
    
    async with get_session() as session:
        query = select(db.Styles.product_id).where(
            db.Styles.product_id.in_(df["product_id"].unique())
        )
        resp = (await session.execute(query)).all()
        styles = pd.DataFrame(resp)

    # Ensure that all product ids are unique
    if len(df['product_id'].unique()) != len(df):
        raise HTTPException(422, "The product ids must be unique")
    
    # Ensure that all product ids exist in the database
    if len(styles) != len(df):
        raise HTTPException(422, "Some product ids not found")
    


    # Start a transaction to update the database records
    async with get_session() as session:
        for _, row in df.iterrows():
            # Prepare values to update
            values = {
                "cost": int(row['cost']),
                "status": "Commercial",
                "updated_by": user_id,
                "updated_at": datetime.now(),
            }
            # Create the update query using product_id as the key
            query = (
                update(db.Styles)
                .where(db.Styles.product_id == row["product_id"])
                .values(**values)
            )
            # Execute the update query
            await session.execute(query)

            # Log the update in the ProductUpdateLog table
            log_entry = db.ProductUpdateLog(
                user_id=user_id,
                email=user_email,
                product_id=row["product_id"],
                timestamp=datetime.now(),
                changes_summary=f"Cost updated to {row['cost']} using importing! Also, product status updated from Merchandise to Commercial."
            )

            session.add(log_entry)

            style_id_email_query = await session.execute(select(db.Styles.style_id).where(db.Styles.product_id == row["product_id"]))
            style_id_email = style_id_email_query.scalar()
            await send_email_status_update("Merchandise", "Commercial", style_id_email, row["product_id"], user_email, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

async def upload_ids(df, user_id, user_email):
    async with get_session() as s:
        query = (
            select(db.Sizes.ean, db.Styles.product_id)
            .join(db.Styles)
            .where(db.Sizes.ean.in_(df["ean"].unique()))
            .where(db.Styles.status == "Approved")
        )
        resp = (await s.execute(query)).all()
        resp = pd.DataFrame(resp)
        unique_eans = resp["ean"].unique()
        unique_product_ids = resp["product_id"].unique()

        if len(unique_eans) != len(df):
            raise HTTPException(422, "Some eans not found or are not Approved")

        query = select(
            db.Sizes.ean, db.Sizes.myntra_id, db.Sizes.ajio_id, db.Sizes.ajio_ean
        ).where(db.Sizes.ean.in_(df["ean"].unique()))
        resp = (await s.execute(query)).all()
        sizes = pd.DataFrame(resp)
    
    product_update_logs_ids = {}
    async with get_session() as s:
        for _, row in df.iterrows():
            values = {}
            if not pd.isnull(row["myntra_id"]):
                if sizes[sizes["ean"] == row["ean"]]["myntra_id"].values[0]:
                    raise HTTPException(422, "Some EANs already have a myntra_id")
                values["myntra_id"] = int(row["myntra_id"])
            if not pd.isnull(row["ajio_id"]):
                if sizes[sizes["ean"] == row["ean"]]["ajio_id"].values[0]:
                    raise HTTPException(422, "Some EANs already have a ajio_id")
                values["ajio_id"] = int(row["ajio_id"])
            if not pd.isnull(row["ajio_ean"]):
                if sizes[sizes["ean"] == row["ean"]]["ajio_ean"].values[0]:
                    raise HTTPException(422, "Some EANs already have a ajio_ean")
                values["ajio_ean"] = int(row["ajio_ean"])
            if values:
                query = (
                    update(db.Sizes)
                    .where(db.Sizes.ean == int(row["ean"]))
                    .values(values)
                )
                await s.execute(query)

                product_id_query = select(db.Sizes.product_id).where(db.Sizes.ean == int(row["ean"]))
                product_id_product_update_log = (await s.execute(product_id_query)).scalar()
                
                if product_id_product_update_log not in product_update_logs_ids:
                    product_update_logs_ids[product_id_product_update_log] = {
                        "eans": []
                    }
                product_update_logs_ids[product_id_product_update_log]["eans"].append({
                    "ean": int(row["ean"]),
                    "myntra_id": int(row["myntra_id"]),
                    "ajio_id": int(row["ajio_id"]),
                    "ajio_ean": int(row["ajio_ean"])
                })

        query = (
            update(db.Styles)
            .where(db.Styles.product_id.in_(unique_product_ids))
            .values({"updated_by": user_id, "updated_at": datetime.now()})
        )
        await s.execute(query)

        # Log the update in the ProductUpdateLog table
        for product_id, data in product_update_logs_ids.items():
            log_entry = db.ProductUpdateLog(
                user_id=user_id,
                email=user_email,
                product_id=product_id,
                timestamp=datetime.now(),
                changes_summary = (
                    f"IDs Imported from CSV:\n"
                    f"{data['eans']}\n"
                )
            )
            s.add(log_entry)

async def upload_dates(df, user_id, user_email):
    try:
        df["first_grn_date"] = pd.to_datetime(df["first_grn_date"])
        df["first_live_date"] = pd.to_datetime(df["first_live_date"])
        df["first_sold_date"] = pd.to_datetime(df["first_sold_date"])
    except Exception:
        raise HTTPException(422, "Some dates are not in the format: YYYY-MM-DD")

    async with get_session() as s:
        query = select(
            db.Styles.product_id,
            db.Styles.first_grn_date,
            db.Styles.first_live_date,
            db.Styles.first_sold_date,
        ).where(db.Styles.product_id.in_(df["product_id"].unique()))
        resp = (await s.execute(query)).all()
        styles = pd.DataFrame(resp)

    if not len(styles):
        raise HTTPException(422, "No products found")

    async with get_session() as s:
        for _, row in df.iterrows():
            values = {"updated_by": user_id, "updated_at": datetime.now()}
            if not pd.isnull(row["first_grn_date"]):
                if styles[styles["product_id"] == row["product_id"]][
                    "first_grn_date"
                ].values[0]:
                    raise HTTPException(
                        422, "Some products already have a first_grn_date"
                    )
                values["first_grn_date"] = row["first_grn_date"]
            if not pd.isnull(row["first_live_date"]):
                if styles[styles["product_id"] == row["product_id"]][
                    "first_live_date"
                ].values[0]:
                    raise HTTPException(
                        422, "Some products already have a first_live_date"
                    )
                values["first_live_date"] = row["first_live_date"]
            if not pd.isnull(row["first_sold_date"]):
                if styles[styles["product_id"] == row["product_id"]][
                    "first_sold_date"
                ].values[0]:
                    raise HTTPException(
                        422, "Some products already have a first_sold_date"
                    )
                values["first_sold_date"] = row["first_sold_date"]
            if values:
                query = (
                    update(db.Styles)
                    .where(db.Styles.product_id == row["product_id"])
                    .values(values)
                )
                await s.execute(query)
                
                summary = "Dates updated using importing:\n"
                if "first_grn_date" in values:
                    summary += f"  First GRN Date: {values['first_grn_date'].date()}\n"
                if "first_live_date" in values:
                    summary += f"  First Live Date: {values['first_live_date'].date()}\n"
                if "first_sold_date" in values:
                    summary += f"  First Sold Date: {values['first_sold_date'].date()}\n"

                log_entry = db.ProductUpdateLog(
                    user_id=user_id,
                    email=user_email,
                    product_id=row["product_id"],
                    timestamp=datetime.now(),
                    changes_summary=summary
                )
                s.add(log_entry)


def get_direct_download_url(url):
    """Converts various cloud storage URLs to direct download links if necessary."""
    if "drive.google.com" in url:
        base_drive_url = "https://drive.google.com/uc?export=download&id="
        file_id = url.split('/d/')[1].split('/view')[0]
        direct_url = f"{base_drive_url}{file_id}"
        logger.info("Direct download URL prepared: " + direct_url)
        return direct_url
    logger.info("No conversion needed, returning original URL.")
    return url

'''

async def upload_images(df, user_id):
    bucket_name = "tigc-chanakya"
    foldername = "uploaded_images"
    s3_client = boto3.client('s3')
    base_s3_url = f"https://{bucket_name}.s3.ap-south-1.amazonaws.com/"

    df['product_id'].fillna("unknown", inplace=True)
    product_ids = df["product_id"].unique()

    async with db.get_session() as s:
        try:
            # Check existing product IDs in the database
            query = select(db.Styles.product_id).where(db.Styles.product_id.in_(product_ids))
            resp = await s.execute(query)
            existing_product_ids = {row[0] for row in resp.fetchall()}
            logger.info("Database query for product IDs completed.")

            for product_id in existing_product_ids:
                logger.info(f"Processing product {product_id}")
                row = df[df['product_id'] == product_id].iloc[0]

                # Sample tag names and URLs for demonstration
                tag_image_urls =[]
                tag_names = ['tag1', 'tag2', 'tag3']
                for tag_name in tag_names:
                    tag_url_query = select([db.Tag.tag_url_column]).where(db.Tag.tag_name == tag_name)
                    tag_url_result = await s.execute(tag_url_query)
                    tag_url_row = tag_url_result.scalar()

                    if tag_url_row:
                        tag_image_urls.append(tag_url_row)
                
                #tag_image_urls = [
                   # 'https://drive.google.com/file/d/1jmr2-c8jcfQ1wlHgd8gFiumq6HAPBbdC/view?usp=drive_link',
                   # 'https://drive.google.com/file/d/1jmr2-c8jcfQ1wlHgd8gFiumq6HAPBbdC/view?usp=drive_link',
                   # 'https://drive.google.com/file/d/1jmr2-c8jcfQ1wlHgd8gFiumq6HAPBbdC/view?usp=drive_link'
                #]
                
                logger.info("tag urls collected")
                
                img_list = []

                # Process the first image with tags
                first_image_url = row['image1']
                if pd.notna(first_image_url):
                    if tag_image_urls:
                        result_path = add_tags_to_image(product_id, first_image_url, foldername, bucket_name, tag_image_urls)
                        if result_path:
                            img_list.append(result_path)
                            logger.info(f"Image with tags processed and uploaded for product {product_id}")

                # Process the remaining images
                for i in range(2, 6):
                    image_url = row[f'image{i}']
                    if pd.notna(image_url) and image_url.startswith('http'):
                        try:
                            direct_url = get_direct_download_url(image_url)
                            response = requests.get(direct_url, timeout=10)
                            response.raise_for_status()

                            if 'image' in response.headers['Content-Type']:
                                image_bytes = BytesIO(response.content)
                                exportid = str(uuid4())
                                datetime_now = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
                                filename = f"{foldername}/{product_id}--{i-1}--{datetime_now}-{exportid}.webp"
                                full_s3_path = f"{base_s3_url}{filename}"

                                s3_client.put_object(
                                    Bucket=bucket_name,
                                    Body=image_bytes.getvalue(),
                                    Key=filename,
                                    ContentType='image/webp'
                                )
                                img_list.append(full_s3_path)
                                logger.info(f"Uploaded image {filename} to S3 successfully.")
                        except Exception as e:
                            logger.error(f"Error processing image {i} for product {product_id}: {str(e)}")

                if img_list:
                    # Update database with new image URLs
                    query = update(db.Styles).where(db.Styles.product_id == product_id).values(
                        images=str(img_list), updated_by=user_id, updated_at=datetime.now()
                    )
                    await s.execute(query)
                    logger.info(f"Database updated with new images for product {product_id}.")

            await s.commit()
            logger.info("All specified products have been processed successfully.")
        except Exception as e:
            logger.error(f"An error occurred during the image upload process: {str(e)}")
            await s.rollback()
            raise
'''

s3_client = boto3.client('s3')
bucket_name = "tigc-chanakya"
foldername = "upload_images"
base_s3_url = f"https://{bucket_name}.s3.ap-south-1.amazonaws.com/"

async def upload_images(df, user_id, user_email):
    df['product_id'].fillna("unknown", inplace=True)
    product_ids = df["product_id"].unique()

    async with db.get_session() as s:
        try:
            # Check existing product IDs in the database
            query = select(db.Styles.product_id).where(db.Styles.product_id.in_(product_ids))
            resp = await s.execute(query)
            existing_product_ids = {row[0] for row in resp.fetchall()}
            logger.info("Database query for product IDs completed.")

            for product_id in existing_product_ids:
                logger.info(f"Processing product {product_id}")
                row = df[df['product_id'] == product_id].iloc[0]

                # Sample tag names and URLs for demonstration
                tags_query = select([db.Styles.tags]).where(db.Styles.product_id == product_id)
                tags_result = await s.execute(tags_query)
                tags_row = tags_result.scalar()

                if tags_row:
                # Assuming tags are stored as a comma-separated string
                    tag_names = tags_row.split(',')

                    logger.info("Tag names collected")
                else:
                    tag_names = []

                    logger.warning(f"No tags found for product_id {product_id}")
                    
                normalized_tag_names = [tag_name.replace(" ", "").lower() for tag_name in tag_names]
                #tag_names = ['tag1', 'tag2', 'tag3']
                tag_url_query = select([db.Tag.tag_url_column]).where(db.Tag.tag_name.in_(normalized_tag_names))
                tag_url_result = await s.execute(tag_url_query)
                tag_url_rows = tag_url_result.fetchall()

                tag_image_urls = [row[0] for row in tag_url_rows]

                logger.info("Tag URLs collected")

                img_list = []

                # Process the first image with tags
                first_image_url = row['image1']
                if pd.notna(first_image_url):
                    if tag_image_urls:
                        result_path = add_tags_to_image(product_id, first_image_url, foldername, bucket_name, tag_image_urls)
                        if result_path:
                            img_list.append(result_path)
                            logger.info(f"Image with tags processed and uploaded for product {product_id}")

                # Process the remaining images
                for i in range(2, 6):
                    image_url = row[f'image{i}']
                    if pd.notna(image_url) and image_url.startswith('http'):
                        try:
                            direct_url = get_direct_download_url(image_url)
                            response = requests.get(direct_url, timeout=10)
                            response.raise_for_status()

                            if 'image' in response.headers['Content-Type']:
                                image_bytes = BytesIO(response.content)
                                exportid = str(uuid4())
                                datetime_now = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
                                filename = f"{foldername}/{settings.env}-{datetime_now}-{exportid}.webp"
                                full_s3_path = f"{base_s3_url}{filename}"

                                # Debug log before upload
                                logger.debug(f"Uploading image {filename} to S3 bucket {bucket_name}")

                                s3_client.put_object(
                                    Bucket=bucket_name,
                                    Body=image_bytes.getvalue(),
                                    Key=filename,
                                    ContentType='image/webp'
                                )

                                # Debug log after successful upload
                                logger.debug(f"Successfully uploaded image {filename} to S3")
                                img_list.append(full_s3_path)
                        except Exception as e:
                            logger.error(f"Error processing image {i} for product {product_id}: {str(e)}")

                if img_list:
                    # Update database with new image URLs
                    query = update(db.Styles).where(db.Styles.product_id == product_id).values(
                        images=str(img_list), updated_by=user_id, updated_at=datetime.now()
                    )
                    await s.execute(query)
                    logger.info(f"Database updated with new images for product {product_id}.")

                    log_entry = db.ProductUpdateLog(
                        user_id=user_id,
                        email=user_email,
                        product_id=product_id,
                        timestamp=datetime.now(),
                        changes_summary=f"Images updated using importing!"
                    )
                    s.add(log_entry)

            await s.commit()
            logger.info("All specified products have been processed successfully.")
        except Exception as e:
            logger.error(f"An error occurred during the image upload process: {str(e)}")
            await s.rollback()
            raise


@router.post("/")
async def bulk_update(file: UploadFile, user=Depends(get_user_from_token)):
    """
    Input: Upload a File

    Can bulk update ean, ids(myntra id, ajio id, etc), dates(first grn, first sold, first live)
    """
    logger.info(f"{user['name']} is trying to upload file: {file.file}")
    df = pd.read_csv(file.file)
    file_id = ",".join(df.columns)

    if file_id not in [
        "product_id,standard_size,ean,mrp,cost",
        "product_id,cost",
        "product_id,image1,image2,image3,image4,image5",
        "style_id,ean,myntra_id,ajio_id,ajio_ean",
        "product_id,first_grn_date,first_live_date,first_sold_date",
    ]:
        raise HTTPException(
            status_code=404, detail="Please select a file from the given templates"
        )

    if file_id == "product_id,standard_size,ean,mrp,cost":
        if not check_if_role_exists(
            user["department"]["roles"], "import ean, mrp, cost", "create"
        ):
            raise HTTPException(
                403, "You don't have permission to import ean, mrp, cost"
            )
        await upload_ean_mrp_cost(df, user["id"], user["email"])

    elif file_id == "product_id,cost":
        if not check_if_role_exists(
            user["department"]["roles"], "import ean, mrp, cost", "create"
        ):
            raise HTTPException(403, "You don't have permission to import cost")
        await update_cost(df, user["id"], user["email"])

    elif file_id == "style_id,ean,myntra_id,ajio_id,ajio_ean":
        if not check_if_role_exists(
            user["department"]["roles"], "import ids", "create"
        ):
            raise HTTPException(403, "You don't have permission to import ids")
        await upload_ids(df[["ean", "myntra_id", "ajio_id", "ajio_ean"]], user["id"], user["email"])

    elif file_id == "product_id,first_grn_date,first_live_date,first_sold_date":
        if not check_if_role_exists(
            user["department"]["roles"], "import grn", "create"
        ):
            raise HTTPException(403, "You don't have permission to import grn")
        await upload_dates(df, user["id"], user["email"])

    elif file_id == "product_id,image1,image2,image3,image4,image5":
        logger.info("Checking permissions for importing images.")
        if not check_if_role_exists(
            user["department"]["roles"], "import images", "create"
        ):
            logger.warning("Permission denied for importing images.")
            raise HTTPException(403, "You don't have permission to import images")
        logger.info("Permissions granted. Starting image upload.")
        await upload_images(df, user["id"], user["email"])
        logger.info("Image upload process completed successfully.") 


    else:
        raise HTTPException(
            status_code=422,
            detail="Please select the correct format and data for the upload",
        )
   
    return {"msg": "Bulk update was a success"}
