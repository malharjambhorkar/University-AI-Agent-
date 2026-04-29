import csv
import os
import re
import warnings
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Optional

warnings.filterwarnings("ignore")

try:
    from langchain.chains import RetrievalQA
    from langchain.text_splitter import CharacterTextSplitter
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_community.llms import Ollama
    from langchain_community.vectorstores import Chroma
except Exception:  # pragma: no cover - keeps the app usable even if optional imports fail
    RetrievalQA = None
    CharacterTextSplitter = None
    HuggingFaceEmbeddings = None
    Ollama = None
    Chroma = None


BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
VECTORSTORE_DIR = os.path.join(BASE_DIR, "vectorstore")
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
SECTION_ALIASES = {
    "HOSTEL RULES": ["hostel", "warden", "room", "visitor"],
    "LIBRARY": ["library", "books", "e-journal", "journal"],
    "EXAMINATION SCHEDULE": ["exam", "semester", "result", "supplementary"],
    "EVENTS & ACTIVITIES": ["event", "fest", "avishkar", "sangram", "hackathon", "codestorm", "sports"],
    "PLACEMENTS": ["placement", "company", "package", "recruiter", "career"],
    "FEES STRUCTURE": ["fee", "fees", "tuition", "scholarship"],
    "CANTEEN & MESS": ["canteen", "mess", "food", "breakfast", "dinner"],
    "IMPORTANT CONTACTS": ["contact", "phone", "helpdesk", "office"],
    "ACADEMIC POLICIES": ["attendance", "leave", "re-evaluation", "policy"],
    "COURSES": ["course", "curriculum", "department", "subject"],
    "ASSIGNMENT DEADLINES": ["deadline", "assignment", "submission"],
    "EXAM SCHEDULE": ["exam date", "exam schedule", "mid semester", "end semester"],
    "IMPORTANT DATES": ["important date", "convocation", "scholarship application"],
    "UPCOMING EVENTS": ["upcoming event", "event date"],
    "PLACEMENT SCHEDULE 2025": ["placement schedule", "campus drive", "mock interview", "aptitude training"],
}


def _safe_read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read().strip()


def load_documents() -> List[Dict[str, str]]:
    documents: List[Dict[str, str]] = []
    for name in sorted(os.listdir(DATA_DIR)):
        if not name.endswith(".txt"):
            continue
        path = os.path.join(DATA_DIR, name)
        documents.append({"name": name, "content": _safe_read_text(path)})
    return documents


def load_feedback() -> List[Dict[str, str]]:
    path = os.path.join(DATA_DIR, "feedback.csv")
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z0-9]+", text.lower())


def _split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [part.strip(" -") for part in parts if part.strip()]


def _keyword_search(query: str, documents: List[Dict[str, str]], limit: int = 5) -> List[str]:
    query_tokens = set(_tokenize(query))
    scored: List[tuple[int, str]] = []
    for document in documents:
        for sentence in _split_sentences(document["content"]):
            if len(_tokenize(sentence)) < 4:
                continue
            sentence_tokens = set(_tokenize(sentence))
            overlap = len(query_tokens & sentence_tokens)
            if overlap:
                scored.append((overlap, sentence))
    scored.sort(key=lambda item: item[0], reverse=True)

    unique_sentences: List[str] = []
    seen = set()
    for _, sentence in scored:
        key = _normalize(sentence)
        if key in seen:
            continue
        unique_sentences.append(sentence)
        seen.add(key)
        if len(unique_sentences) >= limit:
            break
    return unique_sentences


def _find_section_block(query: str, documents: List[Dict[str, str]]) -> List[str]:
    matched_headings = _match_headings(query)
    if not matched_headings:
        return []

    for heading in matched_headings:
        block = _extract_section_lines(heading, documents, limit=6)
        if block:
            return block
    return []


def _match_headings(query: str) -> List[str]:
    query_lower = query.lower()
    matched = []
    for heading, aliases in SECTION_ALIASES.items():
        if any(alias in query_lower for alias in aliases):
            matched.append(heading)
    return matched


def _extract_section_lines(heading: str, documents: List[Dict[str, str]], limit: int = 8) -> List[str]:
    for document in documents:
        lines = [line.rstrip() for line in document["content"].splitlines()]
        for index, line in enumerate(lines):
            if heading in line.upper():
                collected: List[str] = []
                for next_line in lines[index + 1:]:
                    stripped = next_line.strip()
                    if not stripped:
                        continue
                    if stripped.startswith("==="):
                        break
                    collected.append(stripped.lstrip("- ").strip())
                    if len(collected) >= limit:
                        return collected
                return collected
    return []


def _extract_category(query: str, feedback_rows: List[Dict[str, str]]) -> Optional[str]:
    categories = sorted({row.get("Category", "").strip() for row in feedback_rows if row.get("Category")})
    query_lower = query.lower()
    for category in categories:
        if category.lower() in query_lower:
            return category

    aliases = {
        "hostel": "Hostel",
        "room": "Hostel",
        "warden": "Hostel",
        "wifi": "Hostel",
        "faculty": "Faculty",
        "professor": "Faculty",
        "teacher": "Faculty",
        "academic": "Academics",
        "course": "Academics",
        "subject": "Academics",
        "placement": "Placements",
        "company": "Placements",
        "job": "Placements",
        "library": "Library",
        "canteen": "Canteen",
        "food": "Canteen",
        "mess": "Canteen",
        "event": "Events",
        "fest": "Events",
    }
    for keyword, category in aliases.items():
        if keyword in query_lower:
            return category
    return None


def _sentiment_counts(rows: List[Dict[str, str]]) -> Dict[str, int]:
    counts = {"Positive": 0, "Negative": 0, "Neutral": 0}
    for row in rows:
        sentiment = row.get("Sentiment", "").title()
        if sentiment in counts:
            counts[sentiment] += 1
    return counts


def _top_phrases(rows: List[Dict[str, str]], sentiment: Optional[str] = None, limit: int = 3) -> List[str]:
    stop_words = {
        "the", "and", "for", "with", "are", "very", "should", "need", "needs", "this", "that",
        "more", "from", "into", "were", "was", "have", "has", "had", "during", "after", "before",
        "their", "they", "them", "than", "open", "good", "great", "well", "year", "students",
    }
    phrases: Counter[str] = Counter()
    for row in rows:
        if sentiment and row.get("Sentiment", "").title() != sentiment:
            continue
        tokens = [token for token in _tokenize(row.get("Feedback", "")) if token not in stop_words and len(token) > 2]
        phrases.update(tokens)
    return [word.replace("_", " ").title() for word, _ in phrases.most_common(limit)]


def _format_feedback_summary(rows: List[Dict[str, str]], scope: str) -> str:
    if not rows:
        return f"No feedback records were found for {scope}."

    counts = _sentiment_counts(rows)
    positives = [row["Feedback"] for row in rows if row.get("Sentiment", "").title() == "Positive"][:3]
    negatives = [row["Feedback"] for row in rows if row.get("Sentiment", "").title() == "Negative"][:3]
    strengths = _top_phrases(rows, sentiment="Positive")
    concerns = _top_phrases(rows, sentiment="Negative")

    lines = [
        f"Feedback summary for {scope}:",
        f"- Total responses: {len(rows)}",
        f"- Positive: {counts['Positive']}",
        f"- Negative: {counts['Negative']}",
        f"- Neutral: {counts['Neutral']}",
    ]
    if strengths:
        lines.append(f"- Positive themes: {', '.join(strengths)}")
    if concerns:
        lines.append(f"- Concern themes: {', '.join(concerns)}")
    if positives:
        lines.append("- Sample praise:")
        lines.extend([f"  - {item}" for item in positives])
    if negatives:
        lines.append("- Sample concerns:")
        lines.extend([f"  - {item}" for item in negatives])

    recommendation = concerns[0] if concerns else "student experience"
    lines.append(f"- Recommendation: Prioritize improvement around {recommendation.lower()} and review the repeated complaints.")
    return "\n".join(lines)


def _format_report(topic: str, knowledge_points: List[str], feedback_rows: List[Dict[str, str]]) -> str:
    focus = _extract_category(topic, feedback_rows)
    scoped_rows = [row for row in feedback_rows if row.get("Category") == focus] if focus else feedback_rows[:]
    counts = _sentiment_counts(scoped_rows)
    strengths = _top_phrases(scoped_rows, sentiment="Positive")
    concerns = _top_phrases(scoped_rows, sentiment="Negative")
    overview = "; ".join(knowledge_points[:4]) if knowledge_points else "No directly matched knowledge base points were found."

    lines = [
        f"Report Topic: {topic}",
        "",
        "1. Executive Summary",
        f"The review covers {topic.lower()} using the internal knowledge base and available student feedback. Current context suggests: {overview}",
        "",
        "2. Key Findings",
        f"- Knowledge base highlights: {overview}",
        f"- Feedback volume reviewed: {len(scoped_rows)} responses",
        f"- Sentiment split: Positive {counts['Positive']}, Negative {counts['Negative']}, Neutral {counts['Neutral']}",
        "",
        "3. Areas of Strength",
        f"- Recurring positive themes: {', '.join(strengths) if strengths else 'Limited positive themes available'}",
        "",
        "4. Areas Needing Improvement",
        f"- Recurring concern themes: {', '.join(concerns) if concerns else 'Limited complaint themes available'}",
        "",
        "5. Recommendations",
        f"- Address the most repeated concern first: {(concerns[0] if concerns else 'service quality')}.",
        "- Track improvement with short monthly student pulse surveys.",
        "- Publish key updates so students can see progress clearly.",
        "",
        "6. Conclusion",
        "A focused action plan backed by student feedback and university information can improve the overall student support experience.",
    ]
    return "\n".join(lines)


def _knowledge_points_for_topic(topic: str, documents: List[Dict[str, str]], limit: int = 6) -> List[str]:
    points: List[str] = []
    seen = set()

    for heading in _match_headings(topic):
        for item in _extract_section_lines(heading, documents, limit=limit):
            normalized = _normalize(item)
            if normalized in seen:
                continue
            points.append(item)
            seen.add(normalized)
            if len(points) >= limit:
                return points

    category = _extract_category(topic, load_feedback())
    if category == "Hostel":
        for heading in ["HOSTEL RULES", "CANTEEN & MESS", "IMPORTANT CONTACTS"]:
            for item in _extract_section_lines(heading, documents, limit=limit):
                normalized = _normalize(item)
                if normalized in seen:
                    continue
                points.append(item)
                seen.add(normalized)
                if len(points) >= limit:
                    return points

    for item in _keyword_search(topic, documents, limit=limit * 2):
        normalized = _normalize(item)
        if normalized in seen:
            continue
        points.append(item)
        seen.add(normalized)
        if len(points) >= limit:
            break

    return points[:limit]


@dataclass
class AgentDiagnostics:
    llm_available: bool
    retrieval_available: bool
    model_name: str


class UniversityAgent:
    def __init__(self) -> None:
        self.documents = load_documents()
        self.feedback_rows = load_feedback()
        self.llm = self._init_llm()
        self.vectorstore = self._init_vectorstore()
        self.qa_chain = self._init_qa_chain()
        self.diagnostics = AgentDiagnostics(
            llm_available=self.llm is not None,
            retrieval_available=(
                self.qa_chain is not None
                or self.vectorstore is not None
                or bool(self.documents)
            ),
            model_name=DEFAULT_OLLAMA_MODEL,
        )

    def _init_llm(self):
        if Ollama is None:
            return None
        try:
            llm = Ollama(model=DEFAULT_OLLAMA_MODEL, temperature=0.2)
            # Validate the configured local model once during startup so the UI can
            # report availability accurately and avoid repeated failed requests.
            llm.invoke("Reply with exactly: OK")
            return llm
        except Exception:
            return None

    def _init_vectorstore(self):
        if not self.documents or not all([CharacterTextSplitter, HuggingFaceEmbeddings, Chroma]):
            return None

        try:
            embedding = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
            if os.path.exists(VECTORSTORE_DIR) and os.listdir(VECTORSTORE_DIR):
                return Chroma(
                    persist_directory=VECTORSTORE_DIR,
                    embedding_function=embedding,
                )

            splitter = CharacterTextSplitter(chunk_size=700, chunk_overlap=120, separator="\n")
            texts: List[str] = []
            metadatas: List[Dict[str, str]] = []
            for document in self.documents:
                chunks = splitter.split_text(document["content"])
                texts.extend(chunks)
                metadatas.extend([{"source": document["name"]}] * len(chunks))

            db = Chroma.from_texts(
                texts=texts,
                embedding=embedding,
                metadatas=metadatas,
                persist_directory=VECTORSTORE_DIR,
            )
            db.persist()
            return db
        except Exception:
            return None

    def _init_qa_chain(self):
        if self.llm is None or self.vectorstore is None or RetrievalQA is None:
            return None
        try:
            retriever = self.vectorstore.as_retriever(search_kwargs={"k": 4})
            return RetrievalQA.from_chain_type(
                llm=self.llm,
                retriever=retriever,
                return_source_documents=False,
            )
        except Exception:
            return None

    def summarize_feedback(self, query: str = "all feedback") -> str:
        category = _extract_category(query, self.feedback_rows)
        rows = self.feedback_rows
        scope = "all feedback"
        if category:
            rows = [row for row in self.feedback_rows if row.get("Category") == category]
            scope = f"{category.lower()} feedback"

        if self.llm is not None and rows:
            sample = "\n".join(
                f"- [{row.get('Category')} | {row.get('Sentiment')}] {row.get('Feedback')}"
                for row in rows[:12]
            )
            prompt = (
                "You are summarizing student feedback for a university support dashboard.\n"
                f"Scope: {scope}\n"
                f"Feedback:\n{sample}\n\n"
                "Write a concise summary with overall sentiment, top strengths, top issues, and one recommendation."
            )
            try:
                return self.llm.invoke(prompt).strip()
            except Exception:
                pass

        return _format_feedback_summary(rows, scope)

    def generate_report(self, topic: str) -> str:
        knowledge_points = _knowledge_points_for_topic(topic, self.documents, limit=6)
        if self.llm is not None:
            prompt = (
                "You are an academic report generator for a university support assistant.\n"
                f"Topic: {topic}\n"
                f"Knowledge base context:\n- " + "\n- ".join(knowledge_points[:6]) + "\n\n"
                f"Feedback summary context:\n{self.summarize_feedback(topic)}\n\n"
                "Create a structured report with these sections: Executive Summary, Key Findings, "
                "Areas of Strength, Areas Needing Improvement, Recommendations, Conclusion."
            )
            try:
                return self.llm.invoke(prompt).strip()
            except Exception:
                pass
        return _format_report(topic, knowledge_points, self.feedback_rows)

    def retrieve_context(self, query: str, limit: int = 4) -> List[str]:
        if self.vectorstore is not None:
            try:
                docs = self.vectorstore.similarity_search(query, k=limit)
                context = []
                for doc in docs:
                    text = doc.page_content.strip().replace("\n", " ")
                    if text:
                        context.append(text)
                if context:
                    return context
            except Exception:
                pass
        return _keyword_search(query, self.documents, limit=limit)

    def answer_question(self, query: str) -> str:
        section_matches = _find_section_block(query, self.documents)
        if section_matches:
            bullets = "\n".join(f"- {item}" for item in section_matches)
            return f"Here’s the relevant information from the university data:\n{bullets}"

        if self.qa_chain is not None:
            try:
                result = self.qa_chain.invoke({"query": query})
                text = result.get("result", "").strip()
                if text:
                    return text
            except Exception:
                pass

        matches = self.retrieve_context(query, limit=5)
        if matches:
            intro = "Here’s what I found from the university knowledge base:"
            bullets = "\n".join(f"- {item}" for item in matches)
            return f"{intro}\n{bullets}"
        return "I could not find a clear answer in the local university data for that question."

    def run(self, query: str) -> str:
        cleaned_query = query.strip()
        if not cleaned_query:
            return "Please enter a question or topic."

        lowered = cleaned_query.lower()
        if any(keyword in lowered for keyword in ["summarize", "summary", "feedback"]):
            return self.summarize_feedback(cleaned_query)
        if any(keyword in lowered for keyword in ["report", "analysis", "generate"]):
            return self.generate_report(cleaned_query)
        return self.answer_question(cleaned_query)


def create_agent() -> UniversityAgent:
    return UniversityAgent()


if __name__ == "__main__":
    agent = create_agent()
    for sample in [
        "What are the hostel rules?",
        "When is Avishkar tech fest?",
        "Summarize hostel feedback",
        "Generate placement report",
    ]:
        print(f"\nQ: {sample}")
        print(agent.run(sample))
