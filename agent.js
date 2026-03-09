import * as dotenv from 'dotenv';
dotenv.config();
import Anthropic from "@anthropic-ai/sdk";
import readline from "readline";

const apiKey = process.env.ANTHROPIC_API_KEY;

if (!apiKey) {
  console.error("Missing ANTHROPIC_API_KEY. Set it and re-run.");
  process.exit(1);
}

const anthropic = new Anthropic({ apiKey });

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

async function ask(prompt) {
  const resp = await anthropic.messages.create({
    model: "claude-sonnet-4-5",
    max_tokens: 800,
    messages: [{ role: "user", content: prompt }],
  });

  const text = resp.content?.[0]?.text ?? "";
  console.log("\nClaude:\n" + text + "\n");
}

function loop() {
  rl.question("You: ", async (input) => {
    const trimmed = input.trim();
    if (!trimmed) return loop();
    if (trimmed.toLowerCase() === "exit") return rl.close();

    try {
      await ask(trimmed);
    } catch (e) {
      console.error("\nError calling Claude:\n", e?.message ?? e);
    }
    loop();
  });
}

console.log("Claude CLI agent started. Type 'exit' to quit.\n");
loop();
