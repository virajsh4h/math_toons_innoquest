// frontend_hackathon/my-learning-app/src/app/teacher/page.js
"use client";

import { useState, useEffect, useCallback } from "react";
import styles from "./teacher.module.css";
import DetailCard from "../../components/DetailCard";

// --- Dropdown Options ---
const likesOptions = [
  "Apples", "Bananas", "Avocado", "Panda", "Car", "Clock", "Monkey", 
  "Mango", "Dinosaur", "Truck", "Carrot", "Pencil", "Lion", "Bottle", "Tomato",
];
const characterOptions = ["Doraemon", "Chhota Bheem"];

// Map display names to BCP-47 language codes
const languageMap = {
  // ElevenLabs supported (if USE_ELEVENLABS=True)
  "English (ElevenLabs/gTTS)": "en", 
  "Hindi (ElevenLabs/gTTS)": "hi",
  // gTTS Supported (Fallback for en/hi and main for others)
  "Marathi (gTTS)": "mr",
  "Tamil (gTTS)": "ta",
  "Telugu (gTTS)": "te",
  "Kannada (gTTS)": "kn",
  "Malayalam (gTTS)": "ml",
  "Bengali (gTTS)": "bn",
  "Gujarati (gTTS)": "gu",
  "Punjabi (gTTS)": "pa",
  "Urdu (gTTS)": "ur",
  "Assamese (gTTS)": "as",
  "Oriya (gTTS)": "or",
  "Nepali (gTTS)": "ne",
  "Sanskrit (gTTS)": "sa",
  // More languages (add/map BCP-47 codes as needed)
};
const languageOptions = Object.keys(languageMap);


export default function TeacherPage() {
  const [studentDetails, setStudentDetails] = useState({
    name: "Rohan",
    likes: likesOptions[0],
    language: languageOptions[0], // Display name
    character: characterOptions[0],
  });
  const [isTopicModalOpen, setIsTopicModalOpen] = useState(false);
  const [topic, setTopic] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [pollingStatus, setPollingStatus] = useState("idle");
  const [statusMessage, setStatusMessage] = useState("");
  const [taskId, setTaskId] = useState(null);
  const [finalVideoUrl, setFinalVideoUrl] = useState(null);

  const loadStudentDetails = useCallback(() => {
    const savedName = localStorage.getItem("studentName") || "Rohan";
    const savedLanguage = localStorage.getItem("teacherLanguage") || languageOptions[0];
    const savedLikes = localStorage.getItem("teacherLikes") || likesOptions[0];
    const savedCharacter = localStorage.getItem("teacherCharacter") || characterOptions[0];
    
    setStudentDetails({
        name: savedName,
        likes: savedLikes,
        language: savedLanguage,
        character: savedCharacter,
    });
  }, []);


  useEffect(() => {
    loadStudentDetails();
  }, [loadStudentDetails]);

  useEffect(() => {
    if (pollingStatus !== "polling" || !taskId) return;
    const checkStatus = async () => {
      // Use the environment variable for the local backend URL
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;
      const apiUrl = `${API_BASE_URL}/api/v1/check-status/${taskId}`;
      console.log("Attempting to poll status at URL:", apiUrl);
      try {
        const response = await fetch(apiUrl);
        
        if (response.status === 404) {
             // Task might be processing or expired, simply wait for the next poll
             return;
        }
        
        if (!response.ok)
          throw new Error(
            `Failed to check status - Server responded with ${response.status}`
          );
        const data = await response.json();
        
        setStatusMessage(data.message || `Status: ${data.status}`);
        if (data.status === "COMPLETE") {
          setPollingStatus("complete");
          setFinalVideoUrl(data.url); 
        } else if (data.status === "FAILED") {
          setPollingStatus("failed");
          setStatusMessage(`Error: ${data.message}`);
        }
      } catch (error) {
        setPollingStatus("failed");
        setStatusMessage(`Polling Error: ${error.message}`);
      }
    };
    const intervalId = setInterval(checkStatus, 5000);
    return () => clearInterval(intervalId);
  }, [pollingStatus, taskId]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    // Persist latest teacher selections
    if (name === "name") {
      localStorage.setItem("studentName", value);
    } else if (name === "likes") {
        localStorage.setItem("teacherLikes", value);
    } else if (name === "language") {
        localStorage.setItem("teacherLanguage", value);
    } else if (name === "character") {
        localStorage.setItem("teacherCharacter", value);
    }
    setStudentDetails((prev) => ({ ...prev, [name]: value }));
  };

  const resetAndCloseModal = () => {
    setIsTopicModalOpen(false);
    setTopic("");
    setIsLoading(false);
    setPollingStatus("idle");
    setStatusMessage("");
    setTaskId(null);
    setFinalVideoUrl(null);
  };

  const handleInitiateVideoGeneration = async () => {
    if (!topic) {
      alert("Please enter a topic for the video.");
      return;
    }
    setIsTopicModalOpen(true); // Open modal for status updates
    setIsLoading(true);
    setStatusMessage("Sending request to generate video...");
    
    // Use the environment variable for the local backend URL
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;
    const apiUrl = `${API_BASE_URL}/api/v1/generate-video`;
    
    try {
      const formatCharacter = (character) =>
        character.toLowerCase().replace(/ /g, "_");
        
      const selectedLangCode = languageMap[studentDetails.language];
      
      const formatArtifacts = (artifact) => artifact.toLowerCase();

      const payload = {
        student_name: studentDetails.name,
        topic: topic,
        artifacts: [formatArtifacts(studentDetails.likes)],
        character_preset: formatCharacter(studentDetails.character),
        lang: selectedLangCode, // Send the BCP-47 code to the backend
      };

      console.log("Sending Formatted Payload:", payload);

      const response = await fetch(apiUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok)
        throw new Error(`API Error: ${response.status} ${response.statusText}`);

      const data = await response.json();
      if (data.task_id) {
        setTaskId(data.task_id);
        setPollingStatus("polling");
        setStatusMessage(
          "Request accepted. Waiting for video generation to start..."
        );
      } else {
        throw new Error("API did not return a task_id.");
      }
    } catch (error) {
      setStatusMessage(`Error: ${error.message}`);
      setPollingStatus("failed");
    } finally {
      setIsLoading(false);
    }
  };

  const handleApprove = () => {
    if (!finalVideoUrl || !taskId) return;

    // 1. Load existing approved videos
    const approvedVideos = JSON.parse(
      localStorage.getItem("approvedVideos") || "[]"
    );
    
    // 2. Add the new video with its unique ID (task_id) and other metadata
    approvedVideos.push({ 
        id: taskId, 
        title: topic, 
        url: finalVideoUrl,
        lang: languageMap[studentDetails.language]
    });
    
    // 3. Save the updated list back to localStorage
    localStorage.setItem("approvedVideos", JSON.stringify(approvedVideos));
    
    // Optional: Dispatch a storage event to force the student UI to update immediately
    window.dispatchEvent(new Event('storage', { detail: 'approvedVideos' }));

    alert("Video Approved and sent to the student page!");
    resetAndCloseModal();
  };

  return (
    <div className={styles.pageContainer}>
      <main className={styles.mainContent}>
        <h1 className={styles.title}>Teacher's Dashboard</h1>
        <div className={styles.nameInputWrapper}>
          <label htmlFor="name" className={styles.nameLabel}>
            Student Name :
          </label>
          <input
            type="text"
            id="name"
            name="name"
            value={studentDetails.name}
            onChange={handleChange}
            className={styles.nameInput}
          />
        </div>
        <div className={styles.detailsGrid}>
          <DetailCard
            title="Artifact (Like)"
            name="likes"
            value={studentDetails.likes}
            options={likesOptions}
            onChange={handleChange}
          />
          <DetailCard
            title="Language"
            name="language"
            value={studentDetails.language}
            options={languageOptions}
            onChange={handleChange}
          />
          <DetailCard
            title="Character"
            name="character"
            value={studentDetails.character}
            options={characterOptions}
            onChange={handleChange}
          />
        </div>
        <button
          className={styles.createButton}
          onClick={() => {
            // Only open modal if we are not polling or reviewing a video
            if (pollingStatus === 'idle' && !finalVideoUrl) {
                setIsTopicModalOpen(true)
            } else {
                alert("Please wait for the current generation task to finish or discard the video.");
            }
          }}
        >
          Create Video
        </button>
      </main>

      {isTopicModalOpen && (
        <div className={styles.modalOverlay}>
          <div className={styles.modalContent}>
            {/* Modal - Topic Input / Polling Status / Review */}
            {pollingStatus === "idle" && !finalVideoUrl ? (
              <>
                <h2>Create a New Video for {studentDetails.name}</h2>
                <p>
                  Please enter the math topic for the personalized video in <span className={styles.topicLanguage}>{studentDetails.language}</span>.
                </p>
                <input
                  type="text"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  placeholder="e.g., Simple addition with numbers up to 10"
                  className={styles.topicInput}
                />
                <div className={styles.modalActions}>
                  <button
                    onClick={resetAndCloseModal}
                    className={styles.cancelButton}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleInitiateVideoGeneration}
                    disabled={isLoading}
                    className={styles.generateButtonModal}
                  >
                    {isLoading ? "Sending Request..." : "Generate Video"}
                  </button>
                </div>
              </>
            ) : pollingStatus !== "complete" && !finalVideoUrl ? (
              <>
                <h2>Video Generation Status</h2>
                <p className={styles.statusMessage}>
                  Task ID: {taskId || 'N/A'}<br/>
                  Status: {statusMessage}
                </p>
                {(pollingStatus === "failed" || statusMessage.includes("Error:")) && (
                  <button
                    onClick={resetAndCloseModal}
                    className={styles.disapproveButton}
                  >
                    Close
                  </button>
                )}
              </>
            ) : (
              <>
                <h2>Review and Approve Video: {topic}</h2>
                <div className={styles.videoPlayerContainer}>
                  {/* Using the standard HTML video tag for R2 URL playback */}
                  <video
                    src={finalVideoUrl}
                    controls
                    autoPlay
                    className={styles.videoPlayer}
                  >
                    Your browser does not support the video tag.
                  </video>
                </div>
                <div className={styles.modalActions}>
                  <button
                    onClick={resetAndCloseModal}
                    className={styles.disapproveButton}
                  >
                    Discard
                  </button>
                  <button
                    onClick={handleApprove}
                    className={styles.approveButton}
                  >
                    Send to Student
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}