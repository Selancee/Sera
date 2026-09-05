import messages from "./systemMessages.en.json";

const translations: Record<string, string> = messages;
const patterns: Array<[RegExp, (...values: string[]) => string]> = [
  [/^候选 (\d+)$/, (count) => `Candidate ${count}`],
  [/^目标选区中的 (\d+) 个音符全部位于保护范围内；Sera 未越过保护边界。$/, (count) => `All ${count} target notes are protected. Sera respected the protected scope.`],
  [/^已评审 (\d+) 个候选，但它们都触及保护范围；Sera 已全部回滚。$/, (count) => `All ${count} reviewed candidates changed protected content. Sera rolled them all back.`],
  [/^已评审 (\d+) 个候选，但每个候选都会新增音域越界或声部交叉；Sera 已全部拒绝。$/, (count) => `All ${count} reviewed candidates introduced range or voice-crossing issues. Sera rejected them all.`],
  [/^已评审 (\d+) 个候选，但全部未通过乐谱事务验证；原谱没有被修改。$/, (count) => `All ${count} reviewed candidates failed transaction validation. The source score is unchanged.`],
  [/^已评审 (\d+) 个候选，但没有候选同时满足全部硬约束；原谱没有被修改。$/, (count) => `None of the ${count} reviewed candidates satisfied every hard constraint. The source score is unchanged.`],
  [/^LLM 规划失败，已使用确定性理论计划：([\s\S]*)$/, (error) => `LLM planning failed; using a deterministic theory plan: ${error}`],
  [/^本地安全初稿已返回；后台 LLM 优化失败：([\s\S]*)$/, (error) => `Safe local drafts are ready. Background LLM refinement failed: ${error}`],
  [/^(.*?)；和声 (.*?)。修改 (\d+) 个音高；动机 (\d+)，乐句 (\d+)，风格 (\d+)。和弦骨干命中率 (\d+)%[，,]保留原节奏、事件数量、配器与宿主排版。$/, (style, harmony, changed, motif, phrase, profile, ratio) => `${style}; harmony ${harmony}. Changed ${changed} pitches; motif ${motif}, phrase ${phrase}, style ${profile}. Chord-tone ratio ${ratio}%. Original rhythm, event count, instrumentation, and host layout preserved.`]
];

/** Display known system messages in English without modifying API or score data.
 * Unknown provider output, user text, and source material are preserved verbatim.
 */
export function englishSystemText(value: string | null | undefined): string {
  const original = value ?? "";
  if (Object.hasOwn(translations, original)) return translations[original];
  for (const [pattern, translate] of patterns) {
    const match = original.match(pattern);
    if (match) return translate(...match.slice(1));
  }
  return original;
}
