import { useState, Fragment } from "react";
import { useRouter } from "next/router";
import { useFetcher } from "@/context/useFetcher";

// MUI Imports
import Modal from "@mui/material/Modal";

// Component Imports
import {
    DangerButton,
    SubtleButton,
    SimpleButton,
    PrimaryButton,
} from "@/components/base/Buttons";
import DeleteIcon from "@/components/icons/DeleteIcon";
import ErrorIcon from "@/components/icons/ErrorIcon";
import DangerIcon from "@/components/icons/DangerIcon";
import LoadingScreen from "@/components/loadingScreen/LoadingScreen";

// Hook Imports
import { useUserRole, getFeature } from "@/hooks/auth/useUserRole";
import { toast } from "react-toastify";

export default function RejectModal({ info }) {
    const { data, isLoading, error, fetcher } = useFetcher();
    const { userRole, userDepartment, userIsLoading } = useUserRole();
    const router = useRouter();
    const [open, setOpen] = useState(false);
    const [rejectMessage, setRejectMessage] = useState("");
    const [loading, setLoading] = useState(false);
    const [errorMessage, setErrorMessage] = useState("");
    const [isAlertVisible, setIsAlertVisible] = useState(false);
    const handleOpen = () => {
        setOpen(true);
        setRejectMessage("");
        setErrorMessage("");
    };
    const handleClose = () => {
        setOpen(false);
        setLoading(false);
    };

    const handleReject = async () => {
        if (rejectMessage === "") {
            toast.error("Please provide a reason for rejecting this product",
                {
                    position: "top-right",
                    autoClose: 3000,
                    hideProgressBar: false,
                    closeOnClick: true,
                    draggable: true,
                    theme: "colored",
                });
            return;
        }
        try {
            setLoading(true);
            const res = await fetcher(
                `${process.env.NEXT_PUBLIC_PRODUCTS_API}/products/reject/${info?.product_id}`,
                {
                    method: "PUT",
                    body: { rejectMessage },
                }
            );

            if (res?.msg === "Product rejected successfully") {
                setOpen(false);
                setLoading(false);
                setErrorMessage(false);
                setIsAlertVisible(true);
                setTimeout(() => {
                    setIsAlertVisible(false);
                    router.push("/products");
                }, 2500);
            } else {
                setLoading(false);
                // setErrorMessage(true);
                console.log(res, res?.detail)
                setOpen(false);
                setErrorMessage(res?.detail || "Something went wrong, please try again!");
                toast.error(res?.detail || "Something went wrong, please try again!",
                    {
                        position: "top-right",
                        autoClose: 3000,
                        hideProgressBar: false,
                        closeOnClick: true,
                        draggable: true,
                        theme: "colored",
                    });
                // setOpen(true);
            }
        } catch (error) {
            setLoading(false);
            setOpen(false);
            setErrorMessage("Something went wrong, please try again!");
            toast.error("Something went wrong, please try again!",
                {
                    position: "top-right",
                    autoClose: 3000,
                    hideProgressBar: false,
                    closeOnClick: true,
                    draggable: true,
                    theme: "colored",
                });
            // setOpen(true);
        }
    };

    if (userIsLoading) {
        return (
            <></>
            // <DangerButton size={"sm"}>
            //     <p className=" text-sm font-medium leading-5">
            //         Reject
            //     </p>
            // </DangerButton>
        );
    }

    const canReject = getFeature(userRole, "reject product")?.update;

    if (canReject)
        return (
            <Fragment>
                {(info?.deleted === false && info?.status !== "Approved" && info?.status !== "Merchandise" && info?.status !== "Design") ? (
                    <DangerButton size={"sm"} onClick={handleOpen}>
                        <p className=" text-sm font-medium leading-5">
                            Reject
                        </p>
                    </DangerButton>
                ) : <></>}

                <Modal
                    showBackdrop
                    open={open}
                    onClose={handleClose}
                    aria-labelledby="child-modal-title"
                    aria-describedby="child-modal-description"
                >
                    <div className="fixed left-[50%] top-[50%] flex w-[600px] -translate-x-1/2 -translate-y-1/2 flex-col bg-white p-6 shadow-md">
                        {loading ? (
                            <>
                                <div className="flex items-center justify-center p-12">
                                    <LoadingScreen />
                                </div>
                            </>
                        // ) : errorMessage !== "" ? (
                        //     <>
                        //         <div className="flex items-center justify-center">
                        //             <p className="text-sm font-medium text-slate-700">
                        //                 {errorMessage}
                        //             </p>
                        //         </div>
                        //     </>
                        ) : (
                            <>
                                <h2
                                    id="child-modal-title"
                                    className="mb-4 flex items-center gap-2 font-medium leading-5 text-slate-700"
                                >
                                    <ErrorIcon />
                                    Reject {info?.style_id}
                                </h2>
                                <p
                                    id="child-modal-description"
                                    className="mb-8 text-sm font-light text-slate-700"
                                >
                                    {`You are about to reject ${info?.style_id}, are you sure you want to do this?`}
                                </p>
                                <textarea
                                    className="w-full h-32 p-2 mb-4 border border-slate-300 rounded-md"
                                    placeholder="Please provide a reason for rejecting this product"
                                    value={rejectMessage}
                                    onChange={(e) => setRejectMessage(e.target.value)}
                                />
                                <div className="flex gap-2 self-end">
                                    <SubtleButton onClick={handleClose}>Cancel</SubtleButton>
                                    <DangerButton onClick={handleReject}>Reject</DangerButton>
                                </div>
                            </>
                        )}
                    </div>
                </Modal>

                {isAlertVisible && (
                    <div className="alert-container fixed bottom-12 left-24 z-50 max-w-md rounded-md bg-white shadow-lg transition">
                        <div className="flex px-4 py-5">
                            <div className="mr-4">
                                <DangerIcon width={24} height={24} />
                            </div>
                            <div className="mr-4 flex flex-col ">
                                <p className="mb-1 text-sm font-semibold leading-5 text-slate-700">
                                    {"Product rejected successfully"}

                                </p>
                                <p className=" text-sm font-normal text-slate-600">
                                    {info?.style_id} has been{" "}
                                    rejected
                                </p>
                            </div>
                            <div
                                onClick={() => setIsAlertVisible(false)}
                                className="cursor-pointer text-xs text-slate-600 hover:text-slate-800"
                            >
                                &#x2715;
                            </div>
                        </div>
                    </div>
                )}
            </Fragment>
        );
    else return null;
}

