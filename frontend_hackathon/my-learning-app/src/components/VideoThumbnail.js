import styles from "./VideoThumbnail.module.css";

// This is our component. It takes 'props' (properties) as an argument.
// We use { title, icon, color, onClick } to destructure the props object directly.
const VideoThumbnail = ({ title, icon, color, onClick }) => {
  return (
    // The onClick={onClick} part means "when this div is clicked,
    // run the function that was passed in as the onClick prop".
    <div className={`${styles.thumbnail} ${styles[color]}`} onClick={onClick}>
      <span className={styles.title}>{title}</span>
      <span className={styles.icon}>{icon}</span>
    </div>
  );
};

export default VideoThumbnail;
