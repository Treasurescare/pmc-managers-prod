import { forwardRef, useState } from "react";
import { Eye, EyeOff } from "lucide-react";

export const PasswordInput = forwardRef(({ wrapperClassName = "", style, type, ...props }, ref) => { // eslint-disable-line no-unused-vars
  const [show, setShow] = useState(false);
  const id = props["data-testid"] || props.id || "password";
  return (
    <span className={`relative block ${wrapperClassName}`}>
      <input ref={ref} {...props} type={show ? "text" : "password"} style={{ ...style, paddingRight: 40 }} />
      <button type="button" tabIndex={-1} onClick={() => setShow((s) => !s)} aria-label={show ? "Hide password" : "Show password"}
              data-testid={`${id}-toggle`}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-brand-navy/50 hover:text-brand-navy transition-colors">
        {show ? <EyeOff size={18} /> : <Eye size={18} />}
      </button>
    </span>
  );
});
PasswordInput.displayName = "PasswordInput";

export default PasswordInput;
