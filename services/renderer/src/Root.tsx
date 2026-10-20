import { Composition } from "remotion";
import { CourseVideo, CourseVideoProps, FPS, HEIGHT, WIDTH, totalDurationFrames } from "./CourseVideo";

const defaultProps: CourseVideoProps = {
  courseTitle: "Course preview",
  scenes: [
    {
      title: "Welcome",
      bullets: ["What you will learn", "Why it matters"],
      narration: "Welcome to this course.",
      durationSec: 6,
    },
  ],
  narrationSrc: null,
  accentColor: "#38BDF8",
};

export const RemotionRoot: React.FC = () => (
  <Composition
    id="CourseVideo"
    component={CourseVideo}
    fps={FPS}
    width={WIDTH}
    height={HEIGHT}
    durationInFrames={totalDurationFrames(defaultProps.scenes)}
    defaultProps={defaultProps}
    calculateMetadata={({ props }) => ({
      durationInFrames: totalDurationFrames(props.scenes),
    })}
  />
);
