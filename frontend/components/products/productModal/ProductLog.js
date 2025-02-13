import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
dayjs.extend(utc);

const columnNameMapping = {
  target_audience: "Target Audience",
  fit: "Fit",
  gender: "Gender",
  vertical: "Vertical",
  fabric_category: "Fabric Category",
  brand: "Brand",
  usage: "Usage",
  brick: "Brick",
  product: "Product",
  sub_product: "Sub Product",
  barcode_size: "Barcode Size",
  standard_size: "Standard Size",
  ean: "EAN",
  myntra_id: "Myntra ID",
  ajio_id: "Ajio ID",
  ajio_ean: "Ajio EAN",
  garment_waist: "Garment Waist",
  inseam_length: "Inseam Length",
  to_fit_waist: "To Fit Waist",
  across_shoulder: "Across Shoulder",
  chest: "Chest",
  front_length: "Front Length",
  to_fit_foot_length: "To Fit Foot Length",
  shoe_weight: "Shoe Weight",
  outseam_length: "Outseam Length",
  bust: "Bust",
  to_fit_bust: "To Fit Bust",
  hip: "Hip",
  story: "Story",
  colour_family: "Colour Family",
  primary_colour: "Primary Colour",
  secondary_colour: "Secondary Colour",
  tertiary_colour: "Tertiary Colour",
  mrp: "MRP",
  cost: "Cost",
  tags: "Tags",
  season: "Season",
  exclusive: "Exclusive",
  garment_pattern: "Garment Pattern",
  print_pattern_type: "Print Pattern Type",
  number_of_components: "Number of Components",
  number_of_pockets: "Number of Pockets",
  pocket_type: "Pocket Type",
  neck: "Neck",
  collar: "Collar",
  placket: "Placket",
  length: "Length",
  sleeve_length: "Sleeve Length",
  sleeve_type: "Sleeve Type",
  hemline: "Hemline",
  waist_rise: "Waist Rise",
  closure: "Closure",
  footwear_ankle_type: "Footwear Ankle Type",
  footwear_insole: "Footwear Insole",
  dress_type: "Dress Type",
  top_style_type: "Top Style Type",
  jacket_type: "Jacket Type",
  distress: "Distress",
  fade: "Fade",
  dungaree_bottom_type: "Dungaree Bottom Type",
  fabric_code: "Fabric Code",
  fabric_rate: "Fabric Rate",
  fabric_story: "Fabric Story",
  fabric_composition: "Fabric Composition",
  fabric_hsn: "Fabric HSN",
  fabric_weave_pattern: "Fabric Weave Pattern",
  fabric_vendor: "Fabric Vendor",
  denim_cast: "Denim Cast",
  denim_wash: "Denim Wash",
  wash_care: "Wash Care",
  footwear_upper_material: "Footwear Upper Material",
  footwear_sole_material: "Footwear Sole Material",
  first_grn_date: "First GRN Date",
  first_live_date: "First Live Date",
  first_sold_date: "First Sold Date",
  product_description: "Product Description",
  product_id: "Product ID",
  deleted: "Deleted",
  status: "Status",
  images: "Images",
  created_by: "Created By",
  updated_by: "Updated By",
  created_at: "Created At",
  updated_at: "Updated At"
};

const replaceColumnNames = (summary) => {
  if (summary.includes("Product soft deleted")) {
    return "Product soft deleted";
  } else if (summary.includes("Product permanently deleted")) {
    return "Product permanently deleted";
  }

  return summary.replace(/Column '(\w+)' old value/g, (match, p1) => {
    const readableColumn = columnNameMapping[p1] || p1;
    return `Column '${readableColumn}' old value`;
  });
};

export default function ProductLog({ info, logs }) {
  return (
    <>
      <h2 className="mb-8 mt-16 border-b pb-2 text-lg font-medium tracking-wide text-slate-700">
        Update History
      </h2>
      {logs.length>0 ? <div className="mb-24 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-x-8">
        {logs.map((log) => (
          <div className="mb-5 border-b-slate-200 border-b-[1px]" key={log.ProductUpdateLog.id}>
            <p className="mb-2 text-xs leading-3 text-slate-500">
              {dayjs.utc(log.ProductUpdateLog.timestamp).local().format("MMM DD, YYYY h:mm a")}
            </p>
            <p className="mb-2 text-sm leading-5 text-slate-700">{replaceColumnNames(log.ProductUpdateLog.changes_summary)}</p>
            <p className="mb-2 mt-2 text-sm leading-5 text-slate-700">Updated By: {log.ProductUpdateLog.email}</p>
          </div>
        ))}
      </div> : 
      <div className="mb-24 text-slate-500">
        <p>No update history found!</p>
      </div>
      }
      <hr className="mb-0" />
      <div className="flex gap-3 py-4 text-xs text-slate-500">
        <p>
          Last updated at:{" "}
          {dayjs.utc(info.updated_at).local().format("MMM DD, YYYY h:mm a")} by{" "}
          {info?.updated_by}
        </p>{" "}
        |{" "}
        <p>
          Created at:{" "}
          {dayjs.utc(info.created_at).local().format("MMM DD, YYYY h:mm a")} by{" "}
          {info?.created_by}
        </p>
      </div>
    </>
  );
}
