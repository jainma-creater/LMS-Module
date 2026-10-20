import {
  AbsoluteFill,
  Audio,
  Sequence,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

export type CourseScene = {
  title: string;
  kicker: string;
  bullets: string[];
  narration: string;
  durationSec: number;
};

export type CourseVideoProps = {
  courseTitle: string;
  scenes: CourseScene[];
  // Absolute URL of the narration WAV served by the renderer on localhost.
  narrationSrc: string | null;
  accentColor: string;
};

export const FPS = 30;
export const WIDTH = 1280;
export const HEIGHT = 720;

export const totalDurationFrames = (scenes: CourseScene[]): number => {
  const seconds = scenes.reduce((sum, s) => sum + Math.max(1, s.durationSec), 0);
  return Math.max(FPS, Math.round(seconds * FPS));
};

const Background: React.FC<{ accent: string }> = ({ accent }) => (
  <AbsoluteFill
    style={{
      background: "linear-gradient(135deg, #0F172A 0%, #1E293B 100%)",
    }}
  >
    <div
      style={{
        position: "absolute",
        right: -160,
        top: -160,
        width: 480,
        height: 480,
        borderRadius: 240,
        background: accent,
        opacity: 0.12,
      }}
    />
  </AbsoluteFill>
);

const SceneSlide: React.FC<{ scene: CourseScene; index: number; total: number; accent: string }> = ({
  scene,
  index,
  total,
  accent,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const titleIn = spring({ frame, fps, config: { damping: 200 } });
  const fadeOut = interpolate(frame, [durationInFrames - 12, durationInFrames - 2], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ padding: "72px 96px", opacity: fadeOut, color: "#F8FAFC", fontFamily: "Inter, Arial, sans-serif" }}>
      <div style={{ fontSize: 22, letterSpacing: 2, textTransform: "uppercase", color: accent }}>
        {scene.kicker || `${index + 1} of ${total}`}
      </div>
      <div
        style={{
          marginTop: 16,
          fontSize: 64,
          fontWeight: 700,
          lineHeight: 1.1,
          opacity: titleIn,
          transform: `translateY(${(1 - titleIn) * 24}px)`,
        }}
      >
        {scene.title}
      </div>
      <ul style={{ marginTop: 40, fontSize: 32, lineHeight: 1.45, paddingLeft: 36 }}>
        {scene.bullets.map((bullet, i) => {
          const start = 0.6 * fps + i * 0.5 * fps;
          const reveal = interpolate(frame, [start, start + 0.4 * fps], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          return (
            <li key={i} style={{ opacity: reveal, transform: `translateX(${(1 - reveal) * -20}px)` }}>
              {bullet}
            </li>
          );
        })}
      </ul>
      <div
        style={{
          position: "absolute",
          left: 96,
          right: 96,
          bottom: 56,
          padding: "18px 24px",
          borderRadius: 12,
          background: "rgba(15, 23, 42, 0.78)",
          fontSize: 26,
          lineHeight: 1.35,
          color: "#E2E8F0",
        }}
      >
        {scene.narration}
      </div>
    </AbsoluteFill>
  );
};

export const CourseVideo: React.FC<CourseVideoProps> = ({ courseTitle, scenes, narrationSrc, accentColor }) => {
  const { fps } = useVideoConfig();
  let cursor = 0;
  return (
    <AbsoluteFill>
      <Background accent={accentColor} />
      {scenes.map((scene, index) => {
        const from = cursor;
        const duration = Math.max(1, Math.round(scene.durationSec * fps));
        cursor += duration;
        return (
          <Sequence key={index} from={from} durationInFrames={duration}>
            <SceneSlide scene={scene} index={index} total={scenes.length} accent={accentColor} />
          </Sequence>
        );
      })}
      <div
        style={{
          position: "absolute",
          top: 28,
          right: 56,
          fontSize: 20,
          color: "#94A3B8",
          fontFamily: "Inter, Arial, sans-serif",
        }}
      >
        {courseTitle}
      </div>
      {narrationSrc ? <Audio src={narrationSrc} /> : null}
    </AbsoluteFill>
  );
};
