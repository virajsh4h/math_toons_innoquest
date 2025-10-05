// src/components/S3VideoPlayer.js
import styles from "./S3VideoPlayer.module.css";

const S3VideoPlayer = ({ src, onClose }) => {
  if (!src) return null;

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div
        className={styles.videoContainer}
        onClick={(e) => e.stopPropagation()}
      >
        <button className={styles.closeButton} onClick={onClose}>
          &times;
        </button>
        <video
          src={src}
          controls // Shows play, pause, volume, etc.
          autoPlay // Starts the video automatically
          width="100%"
          height="100%"
        >
          Your browser does not support the video tag.
        </video>
      </div>
    </div>
  );
};

export default S3VideoPlayer;
