"use client";
import { useState, useEffect, useCallback } from "react";
import Image from "next/image";
import styles from "./page.module.css";
import VideoThumbnail from "../components/VideoThumbnail";
import S3VideoPlayer from "../components/S3VideoPlayer";

export default function Home() {
  const [selectedVideoUrl, setSelectedVideoUrl] = useState(null);
  const [allVideos, setAllVideos] = useState([]);
  const [studentName, setStudentName] = useState("Student");

  // --- FINAL FIX: Simplified and more robust data loading logic ---
  const loadVideos = useCallback(() => {
    console.log("Loading approved videos and student data from localStorage...");
    
    // Get the videos approved by the teacher. This is the source of truth.
    const approvedByTeacher = JSON.parse(localStorage.getItem("approvedVideos") || "[]");
    
    // Get the student's progress to mark videos as completed.
    const studentProgress = JSON.parse(localStorage.getItem("studentVideos") || "[]");
    const completedUrls = studentProgress
      .filter(v => v.status === 'completed')
      .map(v => v.url);

    // Create the final video list.
    const updatedVideos = approvedByTeacher.map(video => ({
      ...video,
      // If the URL is in the completed list, mark it, otherwise it's 'new'.
      status: completedUrls.includes(video.url) ? 'completed' : 'new'
    }));
    
    setAllVideos(updatedVideos);
    const name = localStorage.getItem("studentName") || "Student";
    setStudentName(name);
    console.log("Videos loaded and merged:", updatedVideos);
  }, []);
  
  useEffect(() => {
    loadVideos();

    // This listener is crucial for real-time updates when the teacher approves a new video.
    const handleStorageChange = (event) => {
      if (event.key === "approvedVideos" || event.key === "studentName" || event.key === "studentVideos") {
        console.log("Storage changed, reloading video data...");
        loadVideos();
      }
    };

    window.addEventListener("storage", handleStorageChange);

    return () => {
      window.removeEventListener("storage", handleStorageChange);
    };
  }, [loadVideos]);

  const handleVideoClose = (watchedUrl) => {
    // Update the student's progress tracker in localStorage
    const studentProgress = JSON.parse(localStorage.getItem("studentVideos") || "[]");
    
    let videoMarked = false;
    const updatedProgress = studentProgress.map(video => {
      if (video.url === watchedUrl) {
        videoMarked = true;
        return { ...video, status: "completed" };
      }
      return video;
    });

    // If the video wasn't already in the student's progress list, add it.
    if (!videoMarked) {
      const watchedVideo = allVideos.find(v => v.url === watchedUrl);
      if (watchedVideo) {
        updatedProgress.push({ ...watchedVideo, status: "completed" });
      }
    }
    
    localStorage.setItem("studentVideos", JSON.stringify(updatedProgress));
    
    // Trigger a visual update by calling loadVideos, which re-reads all storage.
    loadVideos();
    setSelectedVideoUrl(null);
  };

  const newVideos = allVideos.filter((video) => video.status === "new");
  const completedVideos = allVideos.filter(
    (video) => video.status === "completed"
  );

  return (
    <main className={styles.main}>
      <div className={styles.menuIcon}>
        <Image src="/images/menu-icon.svg" alt="Menu" width={50} height={50} />
      </div>
      <div className={styles.profileIcon}>
        <Image
          src="/images/profile.svg"
          alt="User Profile"
          width={60}
          height={60}
        />
      </div>
      <div className={styles.panda}>
        <Image
          src="/images/panda.svg"
          alt="Waving Panda"
          width={200}
          height={200}
        />
      </div>
      <div className={styles.flowers}>
        <Image
          src="/images/flowers.svg"
          alt="Flowers"
          width={200}
          height={200}
        />
      </div>

      <div className={styles.container}>
        <h1 className={styles.title}>Hi {studentName}, let's start learning!</h1>

        <section className={styles.section}>
          <h2 className={styles.subtitle}>
            Watch Video
            <Image src="/images/star.svg" alt="Star" width={40} height={40} />
          </h2>
          <div className={styles.thumbnailGrid}>
            {newVideos.map((video, index) => (
              <VideoThumbnail
                key={index}
                title={video.title}
                icon="▶️"
                color="peach"
                onClick={() => setSelectedVideoUrl(video.url)}
              />
            ))}
            {newVideos.length === 0 && (
              <p>Great job! You've watched all your videos.</p>
            )}
          </div>
        </section>

        {completedVideos.length > 0 && (
          <section className={styles.section}>
            <h2 className={styles.subtitle}>Completed Videos</h2>
            <div className={styles.thumbnailGrid}>
              {completedVideos.map((video, index) => (
                <VideoThumbnail
                  key={index}
                  title={video.title}
                  icon="✅"
                  color="purple"
                  onClick={() => setSelectedVideoUrl(video.url)}
                />
              ))}
            </div>
          </section>
        )}
      </div>

      {selectedVideoUrl && (
        <S3VideoPlayer
          src={selectedVideoUrl}
          onClose={() => handleVideoClose(selectedVideoUrl)}
        />
      )}
    </main>
  );
}