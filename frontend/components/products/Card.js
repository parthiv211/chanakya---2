// Component Imports
import ProductCard from "@/components/products/productCard/ProductCard";
import Link from "next/link";
import { toast } from "react-toastify";

export default function Card({
  options,
  // hierarchy,
  colorFamilies,
  hexCodes,
  // allowedValues,
  // fieldOptions,
  checkboxed,
  setCheckboxed,
}) {
  return (
    <>
      <div className="
        card_container
        flex
        flex-col
        overflow-hidden
        rounded-md
        border
        border-slate-200
        hover:cursor-pointer relative">
        <input className="absolute top-2 left-2 z-[100] w-[20px] h-[20px]" type="checkbox" checked={
          checkboxed.includes(options?.product_id)
        } onChange={() => {
          if (checkboxed.includes(options?.product_id)) {
            setCheckboxed(checkboxed.filter((id) => id !== options?.product_id));
          } else {
            // setCheckboxed([...checkboxed, options?.product_id]);
            let filteredData = [];
            if (options?.brick === "Topwear" && options?.status === "Design") {
              // size, barcode_size, chest, front_length, across_shoulder
              filteredData = options?.completeSizeArray.filter((size) => {
                return size.standard_size != null
                  && size.barcode_size != null
                  && size.chest != null
                  && size.front_length != null
                  && size.across_shoulder != null;
              });
            } else if (options?.brick === "Bottomwear" && options?.status === "Design") {
              // size, barcode_size, garment_waist, inseam_length
              filteredData = options?.completeSizeArray.filter((size) => {
                return size.standard_size != null
                  && size.barcode_size != null
                  && size.garment_waist != null
                  && size.inseam_length != null;
              });
            } else if (options?.brick === "Coordinates" && options?.status === "Design") {
              // size, barcode_size, chest, front_length, across_shoulder, garment_waist, inseam_length
              filteredData = options?.completeSizeArray.filter((size) => {
                return size.standard_size != null
                  && size.barcode_size != null
                  && size.chest != null
                  && size.front_length != null
                  && size.across_shoulder != null
                  && size.garment_waist != null
                  && size.inseam_length != null;
              });
            }
            if (filteredData.length > 0 || options?.brick === "Footwear") {
              setCheckboxed([...checkboxed, options?.product_id]);
            } else {
              toast.error(options?.status === "Design"
                ? "Product does not have all the required fields filled"
                : "Only products with status Design can be bulk updated!", {
                position: "top-right",
                autoClose: 3000,
                hideProgressBar: false,
                closeOnClick: true,
                draggable: true,
                theme: "colored",
              });
            }
          }
        }
        } />
        <Link
          href={`/products/${options?.product_id}`}
          className="
        card_container
        flex
        flex-col
        overflow-hidden
        rounded-md
        border
        border-slate-200
        hover:cursor-pointer"
          target="_blank"
        >
          <ProductCard
            options={options}
            colorFamilies={colorFamilies}
            hexCodes={hexCodes}
          />
        </Link>
      </div>
    </>
  );
}
