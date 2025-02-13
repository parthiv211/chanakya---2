// React Imports
import { useCallback, useMemo, useRef, useState } from "react";

// AG Grid Imports
import { AgGridReact } from "ag-grid-react";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";

// Component Imports
import SectionTitle from "@/components/products/createModal/SectionTitle";

// Lib Imports
import {
  defRows,
  columns,
  changeHideKey,
} from "@/lib/products/getProductSizes";
import { sortSizesFunc } from "@/lib/utils";

export default function ProductSizeGrid(props) {
  const { dataframe, setItem, item, sizes, mode, isDuplicate } = props;
  const productBrick = item.brickField;
  const genderField = item.genderField;
  const productField = item.productField;
  const [targetAudienceFieldDuplication, setTargetAudienceFieldDuplication] = useState(item?.targetAudienceField || "");
  const [fitFieldDuplication, setFitFieldDuplication] = useState(item?.fitField || "");
  const [genderFieldDuplication, setGenderFieldDuplication] = useState(item?.genderField || "");
  const [productFieldDuplication, setProductFieldDuplication] = useState(item?.productField || "");
  const [brickFieldDuplication, setBrickFieldDuplication] = useState(item?.brickField || "");
  const [subProductFieldDuplication, setSubProductFieldDuplication] = useState(item?.subProductField || "");
  const [brandFieldDuplication, setBrandFieldDuplication] = useState(item?.brandField || "");
  const [usageFieldDuplication, setUsageFieldDuplication] = useState(item?.usageField || "");
  const [fabricCategoryFieldDuplication, setFabricCategoryFieldDuplication] = useState(item?.fabricCategoryField || "");

  console.log(productField)
  console.log(productBrick)
  console.log(genderField)
  console.log(item)

  const [columnDefs, setColumnDefs] = useState(columns);

  useMemo(() => {
    setColumnDefs(changeHideKey(columns, productBrick, genderField, productField ));
  }, [productBrick, genderField, productField]);

  const gridRef = useRef();

  const rows = useMemo(() => {
    if (mode === "create" && isDuplicate) {
      if (targetAudienceFieldDuplication !== item.targetAudienceField || fitFieldDuplication !== item.fitField || genderFieldDuplication !== item.genderField || productFieldDuplication !== item.productField || brickFieldDuplication !== item.brickField || subProductFieldDuplication !== item.subProductField || brandFieldDuplication !== item.brandField || usageFieldDuplication !== item.usageField || fabricCategoryFieldDuplication !== item.fabricCategoryField) {
        setTargetAudienceFieldDuplication(item.targetAudienceField);
        setFitFieldDuplication(item.fitField);
        setGenderFieldDuplication(item.genderField);
        setProductFieldDuplication(item.productField);
        setBrickFieldDuplication(item.brickField);
        setSubProductFieldDuplication(item.subProductField);
        setBrandFieldDuplication(item.brandField);
        setUsageFieldDuplication(item.usageField);
        setFabricCategoryFieldDuplication(item.fabricCategoryField);
        let newRows = defRows(dataframe);
        newRows.forEach((row, index) => {
          let item = sizes.find(
            (x) => x.standard_size === row.standard_size && x.barcode_size === row.barcode_size
          );
          if (item) {
            item.ean = null;
            item.myntra_id = null;
            item.ajio_ean = null;
            item.ajio_id = null;
            newRows[index] = item;
          }
        });
        setItem((prev) => ({ ...prev, sizes: newRows }));
        return sortSizesFunc(newRows, "standard_size");
      }
      sizes.forEach((row, index) => {
        row.ean = null;
        row.myntra_id = null;
        row.ajio_ean = null;
        row.ajio_id = null;
        sizes[index] = row;
      });
      return sortSizesFunc(sizes, "standard_size");
    } else if (mode === "create" && !isDuplicate) {
      return sortSizesFunc(defRows(dataframe), "standard_size");
    } else {
      if (targetAudienceFieldDuplication !== item.targetAudienceField || fitFieldDuplication !== item.fitField || genderFieldDuplication !== item.genderField || productFieldDuplication !== item.productField || brickFieldDuplication !== item.brickField || subProductFieldDuplication !== item.subProductField || brandFieldDuplication !== item.brandField || usageFieldDuplication !== item.usageField || fabricCategoryFieldDuplication !== item.fabricCategoryField) {
        setTargetAudienceFieldDuplication(item.targetAudienceField);
        setFitFieldDuplication(item.fitField);
        setGenderFieldDuplication(item.genderField);
        setProductFieldDuplication(item.productField);
        setBrickFieldDuplication(item.brickField);
        setSubProductFieldDuplication(item.subProductField);
        setBrandFieldDuplication(item.brandField);
        setUsageFieldDuplication(item.usageField);
        setFabricCategoryFieldDuplication(item.fabricCategoryField);
        let newRows = defRows(dataframe);
        newRows.forEach((row, index) => {
          let item = sizes.find(
            (x) => x.standard_size === row.standard_size && x.barcode_size === row.barcode_size
          );
          if (item) {
            newRows[index] = item;
          }
        });
        setItem((prev) => ({ ...prev, sizes: newRows }));
        return sortSizesFunc(newRows, "standard_size");
      }
      return sortSizesFunc(sizes, "standard_size");
    }
  }, [dataframe, sizes, isDuplicate, mode]);
 
  console.log(sizes)
  console.log(mode)

  const defaultColDef = useMemo(() => {
    return {
      flex: 1,
      resizable: true,
      minWidth: 140,
    };
  }, []);

  const onCellValueChanged = useCallback(
    (event) => {
      let sizeArray = [...sizes];
      let index = sizeArray.findIndex(
        (x) => x.standard_size === event.data.standard_size
      );
      sizeArray[index] = event.data;
      setItem((prev) => ({ ...prev, sizes: sizeArray }));
    },
    [sizes, setItem]
  );

  const onGridReady = () => {
    setItem((prev) => ({ ...prev, sizes: rows }));
  };

  return (
    <>
      <SectionTitle title="Product Size Chart" />
      <div className="mb-14 w-full">
        {rows.length === 0 && (
          <div>
            <p className="text-center text-gray-500">
              You need to fill all the fields above to see the size chart
            </p>
          </div>
        )}
        {rows.length > 0 && (
          <div>
            <div className="ag-theme-alpine">
              <AgGridReact
                ref={gridRef}
                rowData={rows}
                columnDefs={columnDefs}
                defaultColDef={defaultColDef}
                onCellValueChanged={onCellValueChanged}
                onGridReady={onGridReady}
                detailRowAutoHeight={true}
                domLayout="autoHeight"
              ></AgGridReact>
            </div>
          </div>
        )}
      </div>
    </>
  );
}

