"""Generate synthetic meeting transcript data for training."""
import csv
import random
from pathlib import Path

from src.config import DATA_DIR, TRANSCRIPTS_PATH, RANDOM_STATE

random.seed(RANDOM_STATE)

SPEAKERS = ["Alice", "Bob", "Carol", "Dave", "Eve", "Frank", "Grace", "Hank"]

TOPICS = [
    {
        "theme": "Project Sprint Planning",
        "context": "software development team",
        "members": ["Alice", "Bob", "Carol", "Dave"],
        "important_segments": [
            ("Alice", "We need to finalize the API design by Friday March 15."),
            ("Bob", "I will prepare the database schema and send it to Carol by Thursday."),
            ("Carol", "The deployment to AWS should happen next Monday March 25."),
            ("Dave", "Let's schedule a code review meeting for Wednesday at 3 PM."),
            ("Alice", "The deadline for the client demo is April 1st, no extensions."),
            ("Bob", "Action item: create the CI/CD pipeline this week."),
            ("Carol", "We decided to use React for the frontend instead of Vue."),
            ("Dave", "I will follow up with the DevOps team about server access."),
        ],
        "casual_segments": [
            ("Alice", "So how was everyone's weekend?"),
            ("Bob", "Pretty good, I watched that new movie everyone's talking about."),
            ("Carol", "Oh yeah, I heard it was great. I went hiking actually."),
            ("Dave", "Nice, where did you go hiking?"),
            ("Carol", "Up at Mount Wilson, the weather was perfect."),
            ("Alice", "That sounds lovely. Anyway, back to the sprint."),
            ("Bob", "Oh and by the way, the coffee machine on the third floor is broken again."),
            ("Dave", "Yeah I noticed that this morning. Someone should call maintenance."),
            ("Alice", "Haha, that's the third time this month."),
            ("Bob", "At least the one on the fifth floor works."),
        ],
    },
    {
        "theme": "Research Group Meeting",
        "context": "academic research team",
        "members": ["Eve", "Frank", "Grace", "Hank"],
        "important_segments": [
            ("Eve", "The paper submission deadline for ICML is June 15."),
            ("Frank", "I will complete the experimental results section by next week."),
            ("Grace", "We need to revise the literature review based on reviewer feedback."),
            ("Hank", "The budget request for GPU compute time should be submitted to Dr. Smith."),
            ("Eve", "Let's agree on using BERT as our baseline model."),
            ("Frank", "Action item: Grace will prepare the presentation slides for the department seminar."),
            ("Eve", "The collaboration with Stanford starts on May 1st."),
            ("Hank", "We decided to extend our dataset with the 2024 corpus."),
        ],
        "casual_segments": [
            ("Eve", "Did anyone see the email about the faculty lunch today?"),
            ("Frank", "Yeah, I think it's at noon in the common room."),
            ("Grace", "I might skip it, I have so much grading to do."),
            ("Hank", "I heard they're serving pizza this time."),
            ("Grace", "Oh, in that case I might show up."),
            ("Eve", "Haha, the power of pizza. Oh also, has anyone tried the new cafe near the library?"),
            ("Frank", "Yes, their espresso is actually really good."),
            ("Hank", "I prefer the one across the street honestly."),
            ("Eve", "To each their own. So where were we?"),
        ],
    },
    {
        "theme": "Startup Team Standup",
        "context": "early-stage startup",
        "members": ["Alice", "Eve", "Bob", "Grace"],
        "important_segments": [
            ("Alice", "The investor meeting with Sequoia is scheduled for April 10 at 2 PM."),
            ("Eve", "I will finalize the pitch deck and send it to everyone by Monday."),
            ("Bob", "We need to decide on the pricing model before the investor meeting."),
            ("Grace", "Action item: set up the demo environment for the investor presentation."),
            ("Alice", "The user testing results show 87% satisfaction rate."),
            ("Eve", "Let's go with the freemium model for the launch."),
            ("Bob", "The mobile app beta version will be ready by March 28."),
            ("Alice", "We agreed to target the enterprise market first."),
        ],
        "casual_segments": [
            ("Eve", "Has anyone been to that new ramen place downtown?"),
            ("Bob", "Not yet, but I heard it's amazing. Their tonkotsu is supposed to be incredible."),
            ("Grace", "We should all go together sometime."),
            ("Alice", "Definitely, maybe after we close the funding round."),
            ("Eve", "Deal. Also, I saw a funny meme about startup life."),
            ("Bob", "Send it in the group chat!"),
            ("Grace", "So what's the plan for lunch today?"),
            ("Alice", "I brought leftovers, but I'm always down for takeout."),
        ],
    },
    {
        "theme": "Department Budget Review",
        "context": "university department",
        "members": ["Carol", "Dave", "Frank", "Hank"],
        "important_segments": [
            ("Carol", "The total budget for next fiscal year is $2.3 million."),
            ("Dave", "We need to allocate $450,000 for new lab equipment."),
            ("Frank", "The travel budget should be increased to $120,000 for conference attendance."),
            ("Hank", "Action item: Carol will prepare the budget proposal for the dean by April 15."),
            ("Carol", "We decided to prioritize hiring two new faculty positions."),
            ("Dave", "The software licenses renewal costs $85,000 annually."),
            ("Frank", "Let's schedule a follow-up meeting to finalize the allocations."),
            ("Hank", "The grant from NSF for $500,000 has been confirmed."),
        ],
        "casual_segments": [
            ("Carol", "Has anyone tried the new cafeteria menu?"),
            ("Dave", "The pasta station is pretty decent actually."),
            ("Frank", "I miss the old chef who used to make that amazing soup."),
            ("Hank", "Oh yeah, Professor Thompson's famous tomato soup."),
            ("Carol", "Those were the days. Anyway, back to numbers."),
            ("Dave", "Also, the parking situation is terrible this week."),
            ("Frank", "They're doing construction on lot B, it should be done by next month."),
        ],
    },
    {
        "theme": "Student Club Meeting",
        "context": "university student organization",
        "members": ["Alice", "Bob", "Grace", "Hank"],
        "important_segments": [
            ("Alice", "The annual tech fest is on May 20, we need volunteers by May 1."),
            ("Bob", "Action item: create the event registration form by this Friday."),
            ("Grace", "The budget approved by the student council is $5,000."),
            ("Hank", "We should contact Professor Kumar to be the keynote speaker."),
            ("Alice", "Let's confirm the venue booking for the auditorium by April 20."),
            ("Bob", "The sponsorship outreach to companies should start immediately."),
            ("Grace", "We agreed to include a hackathon as part of the fest."),
            ("Hank", "I will handle the social media marketing starting next week."),
        ],
        "casual_segments": [
            ("Grace", "Did you all see the game last night?"),
            ("Hank", "What a comeback in the last quarter!"),
            ("Bob", "I couldn't watch it, I was studying for midterms."),
            ("Alice", "Midterms are the worst. At least they're almost over."),
            ("Hank", "True. Anyone want to grab food after this meeting?"),
            ("Bob", "I'm down, there's a new burger place I want to try."),
            ("Grace", "Count me in too!"),
            ("Alice", "Same here. Let's wrap this up quickly then."),
        ],
    },
]


def _add_filler(text: str) -> str:
    fillers = ["Um", "So", "Well", "You know", "I mean", "Actually", "Like"]
    words = text.split()
    if len(words) > 5 and random.random() < 0.3:
        idx = random.randint(1, min(3, len(words) - 1))
        words.insert(idx, random.choice(fillers))
    return " ".join(words)


def _generate_transcript(topic: dict) -> list[dict]:
    all_segments = []
    for seg in topic["important_segments"]:
        all_segments.append(("important", seg[0], _add_filler(seg[1])))
    for seg in topic["casual_segments"]:
        all_segments.append(("casual", seg[0], _add_filler(seg[1])))

    random.shuffle(all_segments)

    lines = []
    for label, speaker, text in all_segments:
        lines.append({"speaker": speaker, "text": text, "label": label})

    return lines


def generate_dataset() -> list[dict]:
    all_transcripts = []
    for i, topic in enumerate(TOPICS):
        lines = _generate_transcript(topic)
        transcript_text = "\n".join(f"{l['speaker']}: {l['text']}" for l in lines)
        all_transcripts.append({
            "transcript_id": i + 1,
            "theme": topic["theme"],
            "context": topic["context"],
            "num_speakers": len(topic["members"]),
            "transcript": transcript_text,
            "num_important": sum(1 for l in lines if l["label"] == "important"),
            "num_casual": sum(1 for l in lines if l["label"] == "casual"),
        })
    return all_transcripts


def generate_labeled_segments() -> list[dict]:
    rows = []
    tid = 0
    for topic in TOPICS:
        tid += 1
        lines = _generate_transcript(topic)
        for line in lines:
            rows.append({
                "transcript_id": tid,
                "theme": topic["theme"],
                "speaker": line["speaker"],
                "text": line["text"],
                "label": 1 if line["label"] == "important" else 0,
            })
    return rows


def save_dataset():
    transcripts = generate_dataset()
    with open(TRANSCRIPTS_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=transcripts[0].keys())
        writer.writeheader()
        writer.writerows(transcripts)

    segments_path = DATA_DIR / "labeled_segments.csv"
    segments = generate_labeled_segments()
    with open(segments_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=segments[0].keys())
        writer.writeheader()
        writer.writerows(segments)

    print(f"Generated {len(transcripts)} transcripts -> {TRANSCRIPTS_PATH}")
    print(f"Generated {len(segments)} labeled segments -> {segments_path}")
    return transcripts, segments


if __name__ == "__main__":
    save_dataset()