import React from "react";
import styles from "./CustomSpinner.module.css";

interface CustomSpinnerProps {
  loading: boolean;
  label?: string;
}

const CustomSpinner: React.FC<CustomSpinnerProps> = React.memo(({ loading, label }) => {
  if (!loading) return null;

  return (
    <div className={styles.overlay}>
      <div className={styles.spinnerContainer}>
        <div className={styles.pulsingRing} />
        {label && <span className={styles.label}>{label}</span>}
      </div>
    </div>
  );
});

CustomSpinner.displayName = "CustomSpinner";

export default CustomSpinner;
