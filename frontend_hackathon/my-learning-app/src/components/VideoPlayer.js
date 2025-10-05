// Filename: src/components/VideoPlayer.js

import styles from "./VideoPlayer.module.css";

const VideoPlayer = ({ videoId, onClose }) => {
  if (!videoId) return null;

  const videoSrc = `https://www.youtube.com/embed/${videoId}?autoplay=1`;

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div
        className={styles.videoContainer}
        onClick={(e) => e.stopPropagation()}
      >
        <button className={styles.closeButton} onClick={onClose}>
          &times;
        </button>
        <iframe
          src={videoSrc}
          title="YouTube video player"
          frameBorder="0"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
        ></iframe>
      </div>
    </div>
  );
};

export default VideoPlayer;
