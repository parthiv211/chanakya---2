import { FormControl, FormLabel } from "@mui/material";

export default function Iconographics(props) {
    const {
        tagValue,
        iconographicsOnChange,
    } = props;

    const options = ["EASY CARE", "WRINKLE FREE", "MEMORY STRETCH", "COMFORT STRETCH"];

    const selectedValues = tagValue.map(tag => tag.value);

    console.log(tagValue, selectedValues);

    return (
        <>
            <div className="col-span-2 w-full">
                {/* <FormControl>
                    <FormLabel id="exclusive-radio">Iconographics *</FormLabel> */}
                <p className="MuiFormLabel-root MuiFormLabel-colorPrimary css-u4tvz2-MuiFormLabel-root">Iconographics</p>
                <div className="flex flex-row flex-wrap">
                    {options.map((item, index) => {
                        return (
                            <div key={index} className="flex items-center mr-4 cursor-pointer mt-4">
                                <span className="p-[9px] relative inline-block mr-3">
                                    <input
                                        type="checkbox"
                                        id={item}
                                        name={item}
                                        value={item}
                                        className="absolute top-0 left-0 w-full h-full cursor-pointer"
                                        checked={selectedValues.includes(item)}
                                        onChange={iconographicsOnChange}
                                    />
                                </span>
                                <label htmlFor={
                                    item
                                } className="MuiTypography-root MuiTypography-body1 MuiFormControlLabel-label css-ahj2mt-MuiTypography-root cursor-pointer" >{item.toLowerCase().split(' ').map((word) => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}</label>
                            </div>
                        );
                    })}
                </div>
                {/* </FormControl> */}
            </div>
        </>
    );
}
