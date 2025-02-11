import toastSound from "../assets/toastSound.mp3";
import toastError from "../assets/toastError.mp3";

const PlayToastSound = () => {
  const audio = new Audio(toastSound);
  audio.play().catch((error) => {
    console.error("Audio playback failed:", error);
  });
};

const PlayErrorSound = () => {
  const audio = new Audio(toastError);
  audio.play().catch((error) => {
    console.error("Audio playback failed:", error);
  });
};

export { PlayToastSound, PlayErrorSound };
