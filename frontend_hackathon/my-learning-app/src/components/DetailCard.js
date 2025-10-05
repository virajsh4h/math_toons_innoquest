// src/components/DetailCard.js
import styles from "./DetailCard.module.css";

const DetailCard = ({ title, name, value, options, onChange }) => {
  return (
    <div className={styles.card}>
      <div className={styles.cardHeader}>{title}</div>
      <div className={styles.cardBody}>
        <select
          name={name}
          value={value}
          onChange={onChange}
          className={styles.selectDropdown}
        >
          {options.map((option, index) => (
            <option key={index} value={option}>
              {option}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
};

export default DetailCard;
