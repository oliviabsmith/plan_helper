import toast from "react-hot-toast";

export function useToastError() {
  return (error: unknown, fallback = "Something went wrong") => {
    if (!error) return;
    if (error instanceof Error) {
      toast.error(error.message || fallback);
    } else if (typeof error === "string") {
      toast.error(error);
    } else {
      toast.error(fallback);
    }
  };
}
