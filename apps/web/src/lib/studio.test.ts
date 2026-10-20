import test from "node:test";
import assert from "node:assert/strict";

test("Studio draft course validation", () => {
  const sampleCourse = {
    title: "Enterprise Cybersecurity Standards",
    short_description: "Core defense best practices for corporate users.",
    description: "Detailed walkthrough of security procedures.",
    category: "Information Security",
    difficulty_level: "beginner",
    learning_objectives: [
      "Understand phishing indicators",
      "Follow password standards",
      "Escalate security incidents promptly",
    ],
    key_takeaways: [
      "Never share credentials",
      "Report suspicious emails to the SOC",
    ],
    tags: ["security", "compliance", "phishing"],
    is_mandatory: true,
    validity_days: 365,
    modules: [
      {
        title: "Module 1: Threat Landscape",
        description: "Overview of corporate security threats.",
        lessons: [
          {
            title: "Phishing & Social Engineering",
            description: "Identifying suspicious outreach.",
            content_type: "text",
            content: "Always check sender addresses before clicking links.",
            estimated_minutes: 5,
            is_required: true,
          },
        ],
      },
    ],
    storyboard: [
      {
        scene_number: 1,
        title: "Introduction",
        narration: "Welcome to Enterprise Cybersecurity Standards.",
        visual_prompt: "Security shield animation with company logo.",
        duration_sec: 5,
      },
    ],
    captions_vtt: "WEBVTT\n\n1\n00:00:00.000 --> 00:00:05.000\n[Introduction] Welcome to Enterprise Cybersecurity Standards.\n",
  };

  assert.equal(sampleCourse.title, "Enterprise Cybersecurity Standards");
  assert.equal(sampleCourse.learning_objectives.length, 3);
  assert.equal(sampleCourse.modules[0].lessons[0].is_required, true);
  assert.equal(sampleCourse.storyboard[0].duration_sec, 5);
  assert.ok(sampleCourse.captions_vtt.includes("WEBVTT"));
});

test("Studio draft quiz validation", () => {
  const sampleQuiz = {
    pass_score: 80,
    attempt_limit: 3,
    questions: [
      {
        prompt: "What is the primary action upon receiving a suspected phishing email?",
        question_type: "single_choice",
        options: [
          { id: "a", text: "Forward it to all colleagues" },
          { id: "b", text: "Report it via the PhishAlarm button" },
          { id: "c", text: "Reply asking if it is real" },
        ],
        answer_key: ["b"],
        explanation: "Reporting alerts the security team to analyze and block the malicious sender.",
        difficulty: "easy",
      },
    ],
  };

  assert.equal(sampleQuiz.pass_score, 80);
  assert.equal(sampleQuiz.questions.length, 1);
  const q0 = sampleQuiz.questions[0];
  assert.equal(q0.options.length, 3);
  // Correctness is derived from answer_key (option ids), matching the backend contract.
  const correctOpts = q0.options.filter((o) => q0.answer_key.includes(o.id));
  assert.equal(correctOpts.length, 1);
  assert.equal(correctOpts[0].text, "Report it via the PhishAlarm button");
  for (const opt of q0.options) {
    assert.ok(typeof opt.id === "string" && opt.id.length > 0);
    assert.ok(!("is_correct" in opt), "options must not carry is_correct");
  }
});
