import { describe, expect, it } from "vitest";
import { isMatthewMessage, stripMatthewPrefix } from "../matthewInput";

describe("Matthew input aliases", () => {
  it("routes the Russian name Матвей to the companion", () => {
    expect(isMatthewMessage("Матвей, что думаешь?")).toBe(true);
    expect(stripMatthewPrefix("Матвей, что думаешь?")).toBe("что думаешь?");
  });

  it("accepts the inflected Russian intent form", () => {
    expect(isMatthewMessage("спроси Матвея о свидетеле")).toBe(true);
    expect(stripMatthewPrefix("спроси Матвея о свидетеле")).toBe("о свидетеле");
  });

  it("keeps legacy English routing intact", () => {
    expect(isMatthewMessage("Matthew, what do you think?")).toBe(true);
    expect(stripMatthewPrefix("Matthew, what do you think?")).toBe(
      "what do you think?",
    );
  });
});
