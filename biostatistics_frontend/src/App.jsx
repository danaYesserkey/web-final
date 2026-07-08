import { useEffect, useMemo, useRef, useState } from "react";
import "./App.css";
const API_BASE_URL = "http://127.0.0.1:8000";

function toAbsoluteFileUrl(path) {
  if (!path) return path;
  return /^https?:\/\//i.test(path) ? path : `${API_BASE_URL}${path}`;
}

const DEFAULT_PROFILE = {
  full_name: "Студент",
  email: "",
  group: "",
  specialty: "",
  student_id: "",
  university: "ҚазҰМУ",
  role: "STUDENT",
};

const COURSE_ID = 1;

const LOCAL_PRESENTATIONS = {
  "File.pdf": "/presentations/data-types.pdf",
};

function normalizeModule(rawModule) {
  const lessons = (rawModule.lessons || [])
    .slice()
    .sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
    .map((lesson) => ({
      id: lesson.id,
      module: lesson.module,
      title: lesson.lesson_name,
      order: lesson.order,
    }));

  return {
    id: rawModule.id,
    title: rawModule.module_name,
    description: `${lessons.length} сабақ`,
    order: rawModule.order,
    lessons,
  };
}

function loadJSON(key, fallback) {
  try {
    const saved = localStorage.getItem(key);
    return saved ? JSON.parse(saved) : fallback;
  } catch {
    return fallback;
  }
}

function nowTime() {
  return new Date().toLocaleTimeString("kk-KZ", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getInitials(name) {
  return (
    (name || "ST")
      .split(" ")
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase())
      .join("") || "ST"
  );
}

function getProgressKey(email) {
  const safeEmail = (email || "guest").trim().toLowerCase();
  return `courseProgress_${safeEmail}`;
}

function loadProgressForEmail(email) {
  return loadJSON(getProgressKey(email), {});
}

function saveProgressForEmail(email, progress) {
  if (!email) return;
  localStorage.setItem(getProgressKey(email), JSON.stringify(progress || {}));
}

function App() {
  const [page, setPage] = useState(() =>
    localStorage.getItem("access") || localStorage.getItem("registeredLocal")
      ? "home"
      : "login"
  );

  const [profile, setProfile] = useState(() =>
    loadJSON("studentProfile", DEFAULT_PROFILE)
  );

  const [courseProgress, setCourseProgress] = useState(() => {
    const savedProfile = loadJSON("studentProfile", DEFAULT_PROFILE);
    return loadProgressForEmail(savedProfile.email);
  });

  const [stats, setStats] = useState([]);
  const [statsLoading, setStatsLoading] = useState(false);
  const [statsError, setStatsError] = useState("");

  const [auth, setAuth] = useState(() => ({
    access: localStorage.getItem("access") || "",
    refresh: localStorage.getItem("refresh") || "",
  }));

  const [openedModules, setOpenedModules] = useState({});

  const [course, setCourse] = useState(null);
  const [courseLoading, setCourseLoading] = useState(false);
  const [courseError, setCourseError] = useState("");

  const [activeLesson, setActiveLesson] = useState(null);
  const [lessonLoading, setLessonLoading] = useState(false);
  const [lessonError, setLessonError] = useState("");
  const [lessonScoreLoading, setLessonScoreLoading] = useState(false);
  const [lessonScoreMessage, setLessonScoreMessage] = useState("");

  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Сәлеметсіз бе! Биостатистика бойынша сұрағыңызды жазыңыз. Мен материалдарға сүйеніп, түсінікті жауап беремін.",
    },
  ]);
  const [input, setInput] = useState("");
  const [attachedFiles, setAttachedFiles] = useState([]);
  const [loading, setLoading] = useState(false);

  // Quiz state: the questions and scoring come from Django.
  const [activeQuiz, setActiveQuiz] = useState(null);
  const [quizLoading, setQuizLoading] = useState(false);
  const [quizError, setQuizError] = useState("");
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [quizAnswers, setQuizAnswers] = useState({});
  const [pendingQuiz, setPendingQuiz] = useState(null);

  const fileInputRef = useRef(null);
  const chatEndRef = useRef(null);

  const isLoggedIn = Boolean(auth.access || localStorage.getItem("registeredLocal"));

  const activeModule = useMemo(() => {
    if (!course || !activeLesson) return null;
    return course.modules.find((m) => m.id === activeLesson.module);
  }, [course, activeLesson]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  useEffect(() => {
    if (!isLoggedIn) return;
    loadCourse();
    loadStats();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoggedIn]);

  const saveProfile = (nextProfile) => {
    setProfile(nextProfile);
    localStorage.setItem("studentProfile", JSON.stringify(nextProfile));
    if (nextProfile?.email) {
      localStorage.setItem("currentUserEmail", nextProfile.email);
    }
  };

  const saveCourseProgress = (nextProgress) => {
    const progressToSave = nextProgress || {};
    setCourseProgress(progressToSave);
    saveProgressForEmail(profile?.email, progressToSave);
  };

  const logout = () => {
    localStorage.removeItem("access");
    localStorage.removeItem("refresh");
    localStorage.removeItem("registeredLocal");
    localStorage.removeItem("currentUserEmail");

    setAuth({ access: "", refresh: "" });
    setProfile(DEFAULT_PROFILE);
    setCourseProgress({});
    setPage("login");
  };

  const getApiHeaders = () => {
    const token = auth.access || localStorage.getItem("access") || "";
    const headers = { "Content-Type": "application/json" };

    if (token && !token.startsWith("local-")) {
      headers.Authorization = `Bearer ${token}`;
    }

    return headers;
  };

  const refreshAccessToken = async () => {
    const refreshToken = auth.refresh || localStorage.getItem("refresh") || "";

    if (!refreshToken || refreshToken.startsWith("local-")) {
      return null;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/users/token/refresh/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh: refreshToken }),
      });

      if (!response.ok) return null;

      const data = await response.json().catch(() => ({}));
      if (!data.access) return null;

      localStorage.setItem("access", data.access);
      setAuth((previous) => ({ ...previous, access: data.access }));

      return data.access;
    } catch {
      return null;
    }
  };

  const apiFetch = async (url, options = {}) => {
    const response = await fetch(url, options);

    if (response.status !== 401) {
      return response;
    }

    const newAccess = await refreshAccessToken();

    if (!newAccess) {
      logout();
      return response;
    }

    const headers = { ...(options.headers || {}) };
    if (headers.Authorization) {
      headers.Authorization = `Bearer ${newAccess}`;
    }

    return fetch(url, { ...options, headers });
  };

  const loadCourse = async (courseId = COURSE_ID) => {
    setCourseLoading(true);
    setCourseError("");

    try {
      const response = await apiFetch(`${API_BASE_URL}/api/courses/${courseId}/`, {
        headers: getApiHeaders(),
      });
      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.detail || data.error || "Курс жүктелмеді.");
      }

      setCourse({
        id: data.id,
        title: data.course_name,
        description: data.description,
        modules: (data.modules || [])
          .slice()
          .sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
          .map(normalizeModule),
      });
    } catch (error) {
      setCourseError(error.message);
    } finally {
      setCourseLoading(false);
    }
  };

  const loadStats = async () => {
    setStatsLoading(true);
    setStatsError("");

    try {
      const response = await apiFetch(`${API_BASE_URL}/api/stats/`, {
        headers: getApiHeaders(),
      });
      const data = await response.json().catch(() => ([]));

      if (!response.ok) {
        throw new Error(data.detail || data.error || "Статистика жүктелмеді.");
      }

      setStats(Array.isArray(data) ? data : []);
    } catch (error) {
      setStatsError(error.message);
    } finally {
      setStatsLoading(false);
    }
  };

  const openLesson = async (lesson) => {
    setPage("lesson");
    setLessonLoading(true);
    setLessonError("");
    setActiveLesson(null);

    try {
      const response = await apiFetch(`${API_BASE_URL}/api/lessons/${lesson.id}/`, {
        headers: getApiHeaders(),
      });
      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.detail || data.error || "Сабақты көру үшін алдыңғы сабақты аяқтауыңыз керек");
      }

      setActiveLesson({
        id: data.id,
        module: data.module,
        title: data.lesson_name,
        description: data.description || "",
        order: data.order,
        contents: (data.contents || []).slice().sort((a, b) => a.order - b.order),
        hasAccess: Boolean(data.has_access),
        hasQuiz: Boolean(data.has_quiz),
        canScore: Boolean(data.can_score),
      });
    } catch (error) {
      setLessonError(error.message);
    } finally {
      setLessonLoading(false);
    }
  };

  const markLessonComplete = async (lesson) => {
    if (!lesson || lessonScoreLoading) return;

    setLessonScoreLoading(true);
    setLessonScoreMessage("");

    try {
      const response = await apiFetch(
        `${API_BASE_URL}/api/lessons/${lesson.id}/score/`,
        {
          method: "POST",
          headers: getApiHeaders(),
        }
      );

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.detail || data.error || "Сабақты белгілеу қатесі.");
      }

      const moduleId = lesson.module;
      const currentProgress = courseProgress[moduleId] || {};
      const completed = currentProgress.lessonsCompleted || [];

      saveCourseProgress({
        ...courseProgress,
        [moduleId]: {
          ...currentProgress,
          lessonsCompleted: Array.from(new Set([...completed, lesson.id])),
        },
      });

      setLessonScoreMessage(data.message || "Сабақ аяқталды деп белгіленді.");
      loadStats();
    } catch (error) {
      setLessonScoreMessage(error.message);
    } finally {
      setLessonScoreLoading(false);
    }
  };

  const sendChatMessage = async ({ content, apiContent = content, files = [] }) => {
    const userMessage = {
      role: "user",
      content,
      apiContent,
      files,
      time: nowTime(),
    };

    const nextMessages = [...messages, userMessage];
    setMessages(nextMessages);
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/ai/chat/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: nextMessages.slice(-12).map((msg) => ({
            role: msg.role,
            content: msg.apiContent || msg.content,
          })),
        }),
      });

      const data = await response.json().catch(() => ({}));
      const assistantText =
        data.answer ||
        data.details ||
        data.error ||
        "AI жауап бере алмады. Backend немесе API лимитін тексеріңіз.";

      setMessages((previous) => [
        ...previous,
        { role: "assistant", content: assistantText, time: nowTime() },
      ]);
    } catch (error) {
      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content:
            "Backend-ке қосылу қатесі. Django сервері қосулы ма тексеріңіз: " +
            error.message,
          time: nowTime(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const sendMessage = async () => {
    const text = input.trim();

    if ((!text && attachedFiles.length === 0) || loading) return;

    const files = attachedFiles;
    const fileSummary = files.length
      ? "\n\nТіркелген файлдар: " +
        files.map((file) => `${file.name} (${file.type || "unknown"})`).join(", ")
      : "";

    setInput("");
    setAttachedFiles([]);

    await sendChatMessage({
      content: text || "Файл тіркелді.",
      apiContent: (text || "Студент файл тіркеді.") + fileSummary,
      files,
    });
  };

  const getQuestionText = (question) =>
    question?.text || question?.question || "Сұрақ жүктелмеді.";

  const getQuestionOptions = (question) => {
    const rawOptions =
      question?.answer_options ||
      question?.options ||
      question?.answers ||
      [];

    return rawOptions.map((option, index) => ({
      id: typeof option === "string" ? index : option?.id ?? index,
      text:
        typeof option === "string"
          ? option
          : option?.text || option?.label || String(option ?? ""),
    }));
  };

  const getQuizQuestions = (quiz) =>
    (quiz?.blocks || []).flatMap((block) =>
      (block.questions || []).map((question) => ({
        ...question,
        context: block.context || null,
      }))
    );

  const startLessonQuiz = async (lesson) => {
    setPage("quiz");
    setQuizLoading(true);
    setQuizError("");
    setActiveQuiz({ lesson, quiz: null, questions: [], isSubmitted: false, noQuiz: false });
    setCurrentQuestionIndex(0);
    setQuizAnswers({});

    try {
      const response = await apiFetch(
        `${API_BASE_URL}/api/lessons/${lesson.id}/quiz/`,
        { headers: getApiHeaders() }
      );

      if (response.status === 404) {
        setActiveQuiz({ lesson, quiz: null, questions: [], isSubmitted: false, noQuiz: true });
        return;
      }

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          data.detail ||
            data.error ||
            `Quiz жүктелмеді. Lesson ID: ${lesson.id}`
        );
      }

      const questions = getQuizQuestions(data);

      if (!questions.length) {
        setActiveQuiz({ lesson, quiz: null, questions: [], isSubmitted: false, noQuiz: true });
        return;
      }

      const hasBeenSubmitted = data.score !== null && data.score !== undefined;
      const showReview = hasBeenSubmitted && Boolean(data.passed);
      if (showReview) {
        const prefilledAnswers = {};
        questions.forEach((question) => {
          if (question.user_answer !== undefined) {
            prefilledAnswers[question.id] = question.user_answer;
          }
        });
        setQuizAnswers(prefilledAnswers);
      } else {
        setQuizAnswers({});
      }

      setActiveQuiz({ lesson, quiz: data, questions, isSubmitted: showReview, noQuiz: false });
    } catch (error) {
      setQuizError(error.message);
    } finally {
      setQuizLoading(false);
    }
  };

  const setQuizAnswer = (question, value) => {
    setQuizAnswers((previous) => ({
      ...previous,
      [question.id]: value,
    }));
  };

  const answerTextForChat = (question, answer) => {
    if (Array.isArray(answer)) {
      return getQuestionOptions(question)
        .filter((option) => answer.includes(option.id))
        .map((option) => option.text)
        .join(", ");
    }

    const option = getQuestionOptions(question).find(
      (item) => String(item.id) === String(answer)
    );

    return option?.text || String(answer ?? "");
  };

  const discussWrongQuizAnswer = async (question, answer, canReturnToQuiz) => {
    const visibleText =
      `Мен '` + question.text + `' сұрағына қате жауап бердім. Мен таңдаған жауап: "` +
      `${answerTextForChat(question, answer)}".`;

    setPendingQuiz(
      canReturnToQuiz
        ? { lessonId: activeQuiz?.lesson?.id, lessonTitle: activeQuiz?.lesson?.title }
        : null
    );

    setPage("practice");
    await sendChatMessage({
      content: visibleText,
      apiContent: visibleText,
    });
  };

  const submitQuizAttempt = async () => {
    if (!activeQuiz?.quiz || quizLoading) return;

    const questions = activeQuiz.questions || [];
    const unanswered = questions.find((question) => {
      const value = quizAnswers[question.id];
      return value === undefined || value === null || value === "" ||
        (Array.isArray(value) && value.length === 0);
    });

    if (unanswered) {
      setQuizError("Барлық сұраққа жауап беріңіз.");
      return;
    }

    const answers = questions.map((question) => ({
      question_type: question.question_type || "mcq",
      question_id: question.id,
      user_answer: quizAnswers[question.id],
    }));

    setQuizLoading(true);
    setQuizError("");

    try {
      const response = await apiFetch(
        `${API_BASE_URL}/api/quizzes/${activeQuiz.quiz.id}/submit/`,
        {
          method: "POST",
          headers: getApiHeaders(),
          body: JSON.stringify({ answers }),
        }
      );

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.detail || data.error || "Quiz нәтижесі сақталмады.");
      }

      if (data.message === "Successfully passed quiz before") {
        setPage("course");
        return;
      }

      const lessonId = activeQuiz.lesson.id;
      const moduleId = activeQuiz.lesson.module;
      const score = Number(data.score_percentage ?? 0);
      const currentProgress = courseProgress[moduleId] || {};
      const passedLessons = currentProgress.passedLessons || [];

      saveCourseProgress({
        ...courseProgress,
        [moduleId]: {
          ...currentProgress,
          passedLessons: data.passed
            ? Array.from(new Set([...passedLessons, lessonId]))
            : passedLessons,
          quizScores: [...(currentProgress.quizScores || []), score],
        },
      });

      const resultsByQuestionId = {};
      (data.results || []).forEach((result) => {
        resultsByQuestionId[result.question_id] = result;
      });

      const mergedQuestions = questions.map((question) => {
        const result = resultsByQuestionId[question.id];
        return result
          ? {
              ...question,
              user_answer: result.user_answer,
              is_correct: result.is_correct,
              correct_answer: result.correct_answer,
            }
          : question;
      });

      setActiveQuiz((previous) => ({
        ...previous,
        questions: mergedQuestions,
        isSubmitted: true,
        quiz: {
          ...previous.quiz,
          score: data.score,
          total_questions: data.total_questions,
          score_percentage: data.score_percentage,
          passed: data.passed,
        },
      }));

      setCurrentQuestionIndex(0);
      setQuizError("");
    } catch (error) {
      setQuizError(error.message);
    } finally {
      setQuizLoading(false);
    }
  };

  const resetQuizAttempt = async () => {
    if (!activeQuiz?.quiz || quizLoading) return;

    const hasPassed = Boolean(activeQuiz?.quiz?.passed);

    if (!hasPassed) {
      await startLessonQuiz(activeQuiz.lesson);
      return;
    }

    setQuizLoading(true);
    setQuizError("");

    try {
      const response = await apiFetch(
        `${API_BASE_URL}/api/quizzes/${activeQuiz.quiz.id}/reset/`,
        {
          method: "POST",
          headers: getApiHeaders(),
        }
      );

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.detail || data.error || "Quiz қайта бастау қатесі.");
      }

      await startLessonQuiz(activeQuiz.lesson);
    } catch (error) {
      setQuizError(error.message);
    } finally {
      setQuizLoading(false);
    }
  };

  const goToNextQuizQuestion = () => {
    const questions = activeQuiz?.questions || [];
    const question = questions[currentQuestionIndex];
    const answer = quizAnswers[question?.id];

    if (!activeQuiz?.isSubmitted) {
      if (
        answer === undefined ||
        answer === null ||
        answer === "" ||
        (Array.isArray(answer) && answer.length === 0)
      ) {
        setQuizError("Жауапты таңдаңыз.");
        return;
      }
    }

    setQuizError("");

    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex((value) => value + 1);
      return;
    }

    if (!activeQuiz?.isSubmitted) {
      submitQuizAttempt();
    } else {
      setPage("lesson");
    }
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  };

  const handleFileSelect = (event) => {
    const files = Array.from(event.target.files || []).map((file) => ({
      name: file.name,
      type: file.type,
      size: file.size,
    }));

    if (files.length > 0) {
      setAttachedFiles((prev) => [...prev, ...files]);
      setPage("practice");
    }

    event.target.value = "";
  };

  const quickAsk = (text) => {
    setInput(text);
    setPage("practice");
  };

  if (page === "login") {
    return <LoginPage setPage={setPage} setAuth={setAuth} saveProfile={saveProfile} setCourseProgress={setCourseProgress} />;
  }

  if (page === "register") {
    return (
      <RegisterPage setPage={setPage} setAuth={setAuth} saveProfile={saveProfile} setCourseProgress={setCourseProgress} />
    );
  }

  return (
    <div className="app-shell">
      <TopNav page={page} setPage={setPage} logout={logout} isLoggedIn={isLoggedIn} />

      <input
        ref={fileInputRef}
        type="file"
        className="hidden-file-input"
        multiple
        accept=".csv,.xlsx,.xls,.pdf,.doc,.docx,.ppt,.pptx,image/*"
        onChange={handleFileSelect}
      />

      <main className="app-main">
        {page === "home" && (
          <HomePage profile={profile} setPage={setPage} quickAsk={quickAsk} course={course} />
        )}

        {page === "course" && (
          <CoursePage
            course={course}
            courseLoading={courseLoading}
            courseError={courseError}
            openedModules={openedModules}
            courseProgress={courseProgress}
            openLesson={openLesson}
            toggleModule={(id) =>
              setOpenedModules((prev) => ({ ...prev, [id]: !prev[id] }))
            }
          />
        )}

        {page === "lesson" && (
          <LessonPage
            activeLesson={activeLesson}
            activeModule={activeModule}
            lessonLoading={lessonLoading}
            lessonError={lessonError}
            startLessonQuiz={startLessonQuiz}
            backToCourse={() => setPage("course")}
            markLessonComplete={markLessonComplete}
            lessonScoreLoading={lessonScoreLoading}
            lessonScoreMessage={lessonScoreMessage}
            courseProgress={courseProgress}
            openLesson={openLesson}
          />
        )}

        {page === "quiz" && (
          <QuizPage
            activeQuiz={activeQuiz}
            quizLoading={quizLoading}
            quizError={quizError}
            currentQuestionIndex={currentQuestionIndex}
            quizAnswers={quizAnswers}
            setQuizAnswer={setQuizAnswer}
            goToNextQuizQuestion={goToNextQuizQuestion}
            backToCourse={() => setPage("lesson")}
            discussWrongAnswer={(question) =>
              discussWrongQuizAnswer(question, question.user_answer, true)
            }
            retakeQuiz={resetQuizAttempt}
          />
        )}

        {page === "practice" && (
          <PracticePage
            profile={profile}
            messages={messages}
            input={input}
            setInput={setInput}
            loading={loading}
            attachedFiles={attachedFiles}
            removeFile={(name) =>
              setAttachedFiles((prev) => prev.filter((file) => file.name !== name))
            }
            sendMessage={sendMessage}
            handleKeyDown={handleKeyDown}
            openFilePicker={() => fileInputRef.current?.click()}
            quickAsk={quickAsk}
            chatEndRef={chatEndRef}
            pendingQuiz={pendingQuiz}
            returnToQuiz={() => setPage("quiz")}
          />
        )}

        {page === "profile" && (
          <ProfilePage
            profile={profile}
            setPage={setPage}
            stats={stats}
            statsLoading={statsLoading}
            statsError={statsError}
          />
        )}
      </main>
    </div>
  );
}

function TopNav({ page, setPage, logout }) {
  const links = [
    ["home", "Басты бет"],
    ["course", "Курс"],
    ["practice", "AI чат"],
    ["profile", "Профиль"],
  ];

  return (
    <header className="top-nav">
      <button className="brand" onClick={() => setPage("home")} type="button">
        <strong>BioStat</strong>
        <span>ҚазҰМУ</span>
      </button>

      <nav className="nav-links">
        {links.map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => setPage(key)}
            className={
              page === key || (key === "course" && (page === "lesson" || page === "quiz"))
                ? "active"
                : ""
            }
          >
            {label}
          </button>
        ))}
      </nav>

      <button className="logout-button" type="button" onClick={logout}>
        Шығу
      </button>
    </header>
  );
}

function HomePage({ profile, setPage, quickAsk, course }) {
  const currentModule = course?.modules?.[0]

  return (
    <section className="home-page">
      <div className="page-heading home-heading">
        <p className="page-kicker">BioStat · ҚазҰМУ</p>
        <h1>Қош келдіңіз, {profile.full_name || "студент"}!</h1>
        <p className="page-subtitle"></p>
      </div>

      <div className="home-three-grid">
        <article className="home-action-card">
          <p className="card-label">Курс</p>
          <h2>{currentModule?.title || course?.title || "Курс"}</h2>
          <p className="card-note">Қазіргі модуль</p>
          <button type="button" onClick={() => setPage("course")}>
            Модульді ашу
          </button>
        </article>

        <article className="home-action-card home-action-card-gold">
          <p className="card-label">AI көмекші</p>
          <h2>Сұрағыңызды қойыңыз</h2>
          <div className="quick-action-list">
            <button type="button" onClick={() => quickAsk("Деректер түрлері деген не?")}>
              Деректер түрлері
            </button>
            <button type="button" onClick={() => quickAsk("Қан тобы қандай дерек түріне жатады?")}>
              Қан тобы
            </button>
          </div>
          <button className="gold-action" type="button" onClick={() => setPage("practice")}>
            AI чатты ашу
          </button>
        </article>

        <article className="home-action-card">
          <p className="card-label">Профиль</p>
          <h2>Оқу прогресі</h2>
          <p className="card-note">Нәтижелер мен жеке деректер</p>
          <button type="button" onClick={() => setPage("profile")}>
            Профильді қарау
          </button>
        </article>
      </div>
    </section>
  );
}


function getModuleStats(module, courseProgress) {
  const progress = courseProgress[module.id] || {};
  const lessons = module.lessons || [];
  const completedLessons = progress.lessonsCompleted || [];
  const totalItems = lessons.length;

  if (totalItems === 0) {
    return {
      percent: 0,
      completed: false,
      completedItems: 0,
      totalItems: 0,
      label: "Материалдар әлі қосылмаған",
    };
  }

  const doneItems =
    lessons.filter((lesson) => completedLessons.includes(lesson.id)).length;

  return {
    percent: Math.round((doneItems / totalItems) * 100),
    completed: doneItems === totalItems,
    completedItems: doneItems,
    totalItems,
    label: `${doneItems}/${totalItems} бөлім аяқталды`,
  };
}

function getCourseStats(modules, courseProgress) {
  const moduleStats = modules.map((module) => getModuleStats(module, courseProgress));
  const completedModules = moduleStats.filter((item) => item.completed).length;
  const totalPercent = modules.length
    ? Math.round(moduleStats.reduce((sum, item) => sum + item.percent, 0) / modules.length)
    : 0;

  // Quiz results will be saved later as courseProgress[moduleId].quizScores = [80, 90, ...].
  // Until then the UI honestly shows that no score has been calculated yet.
  const quizScores = modules.flatMap((module) => {
    const scores = courseProgress[module.id]?.quizScores;
    return Array.isArray(scores) ? scores.filter((score) => Number.isFinite(Number(score))) : [];
  });

  const averageScore = quizScores.length
    ? Math.round(quizScores.reduce((sum, score) => sum + Number(score), 0) / quizScores.length)
    : null;

  return {
    completedModules,
    totalModules: modules.length,
    totalPercent,
    moduleStats,
    averageScore,
    quizCount: quizScores.length,
  };
}

function SegmentedProgressBar({ lessons = [], progress = {}, onSegmentClick = null, activeLessonId = null }) {
  if (!lessons.length) return null;

  const completedLessons = progress.lessonsCompleted || [];
  const passedLessons = progress.passedLessons || [];

  return (
    <div className="segmented-progress-bar">
      {lessons.map((lesson, index) => {
        const isCompleted = completedLessons.includes(lesson.id);
        const isQuizPassed = passedLessons.includes(lesson.id);
        const isActive = activeLessonId === lesson.id;

        let status = "not-started";
        if (isQuizPassed) status = "quiz-passed";
        else if (isCompleted) status = "completed";

        let className = `progress-segment ${status}`;
        if (isActive) className += " active";

        const Tag = onSegmentClick ? "button" : "div";
        const elementProps = onSegmentClick
          ? {
              type: "button",
              onClick: (e) => {
                e.stopPropagation();
                onSegmentClick(lesson);
              },
            }
          : {};

        return (
          <Tag
            key={lesson.id}
            className={className}
            title={`${index + 1}. ${lesson.title}`}
            {...elementProps}
          >
            {onSegmentClick && <span className="segment-tooltip">{lesson.title}</span>}
          </Tag>
        );
      })}
    </div>
  );
}

function CoursePage({
  course,
  courseLoading,
  courseError,
  openedModules,
  courseProgress,
  openLesson,
  toggleModule,
}) {
  const modules = course?.modules || [];

  return (
    <section className="page-shell">
      <div className="page-header">
        <span>COURSE</span>
        <h1>{course?.title || "Курс материалдары"}</h1>
        {course?.description && <p>{course.description}</p>}
      </div>

      {courseLoading && <p className="course-status">Курс жүктеліп жатыр...</p>}

      {!courseLoading && courseError && (
        <p className="course-status course-status-error">{courseError}</p>
      )}

      {!courseLoading && !courseError && modules.length === 0 && (
        <p className="course-status">Бұл курста модульдер әлі қосылмаған.</p>
      )}

      <div className="course-layout">
        {modules.map((module) => {
          const isOpen = Boolean(openedModules[module.id]);
          const progress = courseProgress?.[module.id] || {};
          const passedLessons = progress.passedLessons || [];

          return (
            <article className="course-module" key={module.id}>
              <button
                className="course-module-head"
                type="button"
                onClick={() => toggleModule(module.id)}
              >
                <div>
                  <span>{isOpen ? "⌄" : "›"}</span>

                  <div>
                    <h2>{module.title}</h2>
                    <p>{module.description}</p>
                    <SegmentedProgressBar lessons={module.lessons} progress={progress} />
                  </div>
                </div>

                <em>{isOpen ? "Жабу" : "Ашу"}</em>
              </button>

              {isOpen && (
                <div className="course-module-body">
                  <div className="module-lesson-list">
                    {(module.lessons || []).map((lesson) => {
                      const lessonDone = passedLessons.includes(lesson.id);

                      return (
                        <button
                          type="button"
                          className="module-lesson-row"
                          key={lesson.id}
                          onClick={() => openLesson(lesson)}
                        >
                          <span>{lesson.title}</span>
                          {lessonDone && <em className="lesson-done-badge">✓</em>}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}

function LessonContentBlock({ item }) {
  switch (item.type) {
    case "heading": {
      const Tag = `h${Math.min(Math.max(item.h_level || 2, 1), 6)}`;
      return <Tag className="lesson-block-heading">{item.content}</Tag>;
    }

    case "text":
      return (
        <p className={`lesson-block-text lesson-block-text--${item.text_type || "base"}`}>
          {item.content}
        </p>
      );

    case "image":
      return (
        <div className="lesson-block-image">
          <img src={item.content_url} alt="" loading="lazy" />
        </div>
      );

    case "presentation":
      return (
        <PresentationViewer
          fileUrl={item.content_url}
          title="Презентация"
        />
      );

    case "youtube": {
      const isRawIframe = item.content_url?.trimStart().startsWith("<iframe");

      if (isRawIframe) {
        return (
          <div
            className="lesson-block-youtube"
            dangerouslySetInnerHTML={{ __html: item.content_url }}
          />
        );
      }

      return (
        <div className="lesson-block-youtube">
          <iframe
            src={item.content_url}
            title="YouTube video"
            allowFullScreen
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          />
        </div>
      );
    }
    
    case "video":
      return (
        <div className="lesson-block-video">
          <video controls src={item.content_url}>
            Браузер бейнені қолдамайды.
          </video>
        </div>
      );

    default:
      return null;
  }
}

function LessonPage({
  activeLesson,
  activeModule,
  lessonLoading,
  lessonError,
  startLessonQuiz,
  backToCourse,
  markLessonComplete,
  lessonScoreLoading,
  lessonScoreMessage,
  courseProgress,
  openLesson,
}) {
  const moduleProgress = activeLesson
    ? courseProgress?.[activeLesson.module] || {}
    : {};
  const isCompleted = (moduleProgress.lessonsCompleted || []).includes(
    activeLesson?.id
  );

  return (
    <section className="page-shell">
      <div className="quiz-top-row">
        <button type="button" className="back-button" onClick={backToCourse}>
          ← Курсқа оралу
        </button>
      </div>

      {lessonLoading && <p className="course-status">Сабақ жүктеліп жатыр...</p>}

      {!lessonLoading && lessonError && (
        <p className="course-status course-status-error">{lessonError}</p>
      )}

      {!lessonLoading && !lessonError && activeLesson && (
        <>
          {activeModule && (
            <div className="lesson-module-progress-nav">
              <div className="progress-nav-info">
                <span className="module-tag">Модуль: {activeModule.title}</span>
                <span className="progress-ratio">
                  Сабақ {activeModule.lessons.findIndex((l) => l.id === activeLesson.id) + 1} / {activeModule.lessons.length}
                </span>
              </div>
              <SegmentedProgressBar
                lessons={activeModule.lessons}
                progress={moduleProgress}
                onSegmentClick={openLesson}
                activeLessonId={activeLesson.id}
              />
            </div>
          )}

          <div className="page-heading">
            <p className="page-kicker">Сабақ</p>
            <h1>{activeLesson.title}</h1>
            {activeLesson.description && (
              <p className="page-subtitle">{activeLesson.description}</p>
            )}
          </div>

          {!activeLesson.hasAccess && (
            <p className="course-status course-status-error">
              Сабақты көру үшін алдыңғы сабақты аяқтауыңыз керек
            </p>
          )}

          {activeLesson.hasAccess && (
            <>
              <div className="lesson-content-list">
                {activeLesson.contents.length === 0 && (
                  <p className="course-status">Бұл сабаққа материал әлі қосылмаған.</p>
                )}

                {activeLesson.contents.map((item, index) => (
                  <LessonContentBlock key={index} item={item} />
                ))}
              </div>

              {activeLesson.canScore && (
                <div className="module-quiz-card">
                  <div>
                    <span>Сабақ материалы</span>
                    <h3>{isCompleted ? "Сабақ аяқталды" : "Сабақты аяқтадыңыз ба?"}</h3>
                    <p>
                      {lessonScoreMessage ||
                        (isCompleted
                          ? "Бұл сабақ аяқталды деп белгіленген."
                          : "Материалды оқып болғаннан кейін белгілеңіз.")}
                    </p>
                  </div>

                  <button
                    type="button"
                    disabled={lessonScoreLoading}
                    onClick={() => markLessonComplete(activeLesson)}
                  >
                    {lessonScoreLoading
                      ? "Сақталуда..."
                      : isCompleted
                      ? "Қайта белгілеу"
                      : "Аяқталды деп белгілеу"}
                  </button>
                </div>
              )}

              {activeLesson.hasQuiz && (
                <div className="module-quiz-card">
                  <div>
                    <span>Сабақ тесті</span>
                    <h3>Біліміңізді тексеріңіз</h3>
                    <p>Материалды оқығаннан кейін quiz тапсырыңыз.</p>
                  </div>

                  <button type="button" onClick={() => startLessonQuiz(activeLesson)}>
                    Quiz бастау
                  </button>
                </div>
              )}
            </>
          )}
        </>
      )}
    </section>
  );
}

function PresentationViewer({ fileUrl, title }) {
  const [pageNumber, setPageNumber] = useState(1);
  const totalPages = 27;

  const pdfUrl = `${fileUrl}#page=${pageNumber}&zoom=page-fit&toolbar=0&navpanes=0&scrollbar=0`;

  return (
    <div className="presentation-viewer">
      <div className="presentation-toolbar">
        <div>
          <span>Презентация</span>
          <strong>{title || "Презентация"}</strong>
        </div>

        <a href={fileUrl} target="_blank" rel="noreferrer">
          Толық экранда ашу
        </a>
      </div>

      <div className="presentation-native-frame">
        <iframe key={pageNumber} src={pdfUrl} title={`page-${pageNumber}`} />
      </div>

      <div className="presentation-pagination">
        <button
          type="button"
          disabled={pageNumber === 1}
          onClick={() => setPageNumber((p) => Math.max(1, p - 1))}
        >
          ← Алдыңғы
        </button>

        <span>{pageNumber} / {totalPages}</span>

        <button
          type="button"
          disabled={pageNumber === totalPages}
          onClick={() => setPageNumber((p) => Math.min(totalPages, p + 1))}
        >
          Келесі →
        </button>
      </div>
    </div>
  );
}

const getQuestionText = (question) =>
    question?.text || question?.question || "Сұрақ жүктелмеді.";

  const getQuestionOptions = (question) => {
    const rawOptions =
      question?.answer_options ||
      question?.options ||
      question?.answers ||
      [];

    return rawOptions.map((option, index) => ({
      id: typeof option === "string" ? index : option?.id ?? index,
      text:
        typeof option === "string"
          ? option
          : option?.text || option?.label || String(option ?? ""),
    }));
  };

function QuizPage({
  activeQuiz,
  quizLoading,
  quizError,
  currentQuestionIndex,
  quizAnswers,
  setQuizAnswer,
  goToNextQuizQuestion,
  backToCourse,
  discussWrongAnswer,
  retakeQuiz,
}) {
  const questions = activeQuiz?.questions || [];
  const question = questions[currentQuestionIndex];
  const questionType = question?.question_type || "mcq";
  const options = question ? getQuestionOptions(question) : [];
  const selectedAnswer = question ? quizAnswers[question.id] : undefined;
  const isLastQuestion = currentQuestionIndex === questions.length - 1;
  const isSubmitted = Boolean(activeQuiz?.isSubmitted);
  const context = question?.context || null;

  const toggleMultipleOption = (optionId) => {
    if (isSubmitted) return;
    const previous = Array.isArray(selectedAnswer) ? selectedAnswer : [];
    const next = previous.includes(optionId)
      ? previous.filter((id) => id !== optionId)
      : [...previous, optionId];
    setQuizAnswer(question, next);
  };

  const getOptionReviewClass = (option) => {
    if (!isSubmitted) return "";

    const correctAnswer = question?.correct_answer;
    const isMultiple = questionType === "birneshe";

    const isCorrectOption = isMultiple
      ? Array.isArray(correctAnswer) && correctAnswer.includes(option.id)
      : correctAnswer === option.id;

    const isUserPick = isMultiple
      ? Array.isArray(selectedAnswer) && selectedAnswer.includes(option.id)
      : selectedAnswer === option.id;

    if (isCorrectOption && isUserPick) return "selected correct";
    if (isCorrectOption) return "correct-answer";
    if (isUserPick) return "selected incorrect";
    return "";
  };

  return (
    <section className="page-shell quiz-page-shell">
      <div className="quiz-top-row">
        <button type="button" className="back-button" onClick={backToCourse}>
          ← Курсқа оралу
        </button>
        <span>{questions.length ? `${currentQuestionIndex + 1} / ${questions.length}` : ""}</span>
      </div>

      <div className="page-heading">
        <p className="page-kicker">Модуль тесті</p>
        <h1>{activeQuiz?.lesson?.title || "Quiz"}</h1>
        <div className="quiz-score-summary-row">
          {isSubmitted && activeQuiz?.quiz ? (
            <p className="quiz-score-summary">
              Нәтиже: {activeQuiz.quiz.score} / {activeQuiz.quiz.total_questions} (
              {activeQuiz.quiz.score_percentage}%)
            </p>
          ) : (
            <span />
          )}

          {retakeQuiz && (
            <button
              type="button"
              className="quiz-retake-button"
              onClick={retakeQuiz}
            >
              {"Қайта тапсыру"}
            </button>
          )}
        </div>
      </div>

      {quizLoading && <div className="quiz-card">Quiz жүктеліп жатыр...</div>}

      {!quizLoading && quizError && (
        <div className="quiz-card quiz-error">
          <p>{quizError}</p>
        </div>
      )}

      {!quizLoading && !quizError && activeQuiz?.noQuiz && (
        <div className="quiz-card quiz-empty">
          <p>Бұл сабаққа quiz әлі қосылмаған.</p>
          <button type="button" onClick={backToCourse}>
            Курсқа оралу
          </button>
        </div>
      )}

      {!quizLoading && question && (
        <article className="quiz-card">
          {context && (
            <div className="quiz-context">
              {context.title && <h3>{context.title}</h3>}
              {context.text && <p>{context.text}</p>}
              {context.dataset_file && (
                <a
                  href={API_BASE_URL+context.dataset_file}
                  target="_blank"
                  rel="noreferrer"
                  className="quiz-context-file"
                >
                  Файлды ашу
                </a>
              )}
            </div>
          )}

          <p className="quiz-question">{getQuestionText(question)}</p>

          {questionType === "text" ? (
            <input
              className="quiz-text-input"
              value={selectedAnswer || ""}
              onChange={(event) => setQuizAnswer(question, event.target.value)}
              placeholder="Жауапты жазыңыз"
              readOnly={isSubmitted}
            />
          ) : (
            <div className="quiz-options">
              {options.map((option) => {
                const isMultiple = questionType === "birneshe";
                const selected = isMultiple
                  ? Array.isArray(selectedAnswer) && selectedAnswer.includes(option.id)
                  : selectedAnswer === option.id;

                const reviewClass = getOptionReviewClass(option);
                const className = isSubmitted
                  ? reviewClass
                  : selected
                  ? "selected"
                  : "";

                return (
                  <button
                    type="button"
                    key={option.id}
                    className={className}
                    disabled={isSubmitted}
                    onClick={() =>
                      isMultiple
                        ? toggleMultipleOption(option.id)
                        : setQuizAnswer(question, option.id)
                    }
                  >
                    {isMultiple ? (selected ? "✓ " : "□ ") : ""}{option.text}
                  </button>
                );
              })}
            </div>
          )}

          {isSubmitted && questionType === "text" && (
            <p className="quiz-text-correct-answer">
              Дұрыс жауап: {question.correct_answer}
            </p>
          )}

          {isSubmitted && (
            <div className={`quiz-review-indicator ${question.is_correct ? "correct" : "incorrect"}`}>
              <span>{question.is_correct ? "Дұрыс жауап" : "Қате жауап"}</span>
              {!question.is_correct && discussWrongAnswer && (
                <button
                  type="button"
                  className="quiz-discuss-button"
                  onClick={() => discussWrongAnswer(question)}
                >
                  ЖИ-мен бірге талқылау
                </button>
              )}
            </div>
          )}

          <button
            type="button"
            className="quiz-submit-button"
            onClick={goToNextQuizQuestion}
          >
            {isSubmitted
              ? isLastQuestion
                ? "Аяқтау"
                : "Келесі сұрақ"
              : isLastQuestion
              ? "Тестті аяқтау"
              : "Келесі сұрақ"}
          </button>
        </article>
      )}
    </section>
  );
}

function PracticePage({
  profile,
  messages,
  input,
  setInput,
  loading,
  attachedFiles,
  removeFile,
  sendMessage,
  handleKeyDown,
  openFilePicker,
  quickAsk,
  chatEndRef,
  pendingQuiz,
  returnToQuiz,
}) {
  const studentInitials = getInitials(profile.full_name || "Студент");

  return (
    <section className="chat-page">
      <aside className="chat-sidebar">
        <span className="sidebar-label">AI MODE</span>
        <h2>AI көмекші</h2>
        <p>
        </p>

        <button type="button" onClick={() => quickAsk("Деректер түрлері деген не?")}>
          Деректер түрлері
        </button>
        <button
          type="button"
          onClick={() => quickAsk("Қан тобы қандай дерек түріне жатады?")}
        >
          Мысал сұрақ
        </button>
        <button type="button" onClick={openFilePicker}>
          Файл тіркеу
        </button>

        {pendingQuiz && (
          <button type="button" className="return-quiz-button" onClick={returnToQuiz}>
            Тестке оралу
          </button>
        )}
      </aside>

      <section className="chat-workspace">
        <header className="chat-header">
          <div>
            <h1>AI чат</h1>
            <p></p>
          </div>
        </header>

        <div className="chat-stream">
          {messages.map((msg, index) => (
            <ChatMessage key={`${msg.time}-${index}`} msg={msg} initials={studentInitials} />
          ))}

          {loading && (
            <div className="message assistant">
              <div className="bot-avatar">AI</div>
              <div className="message-bubble">
                <p>Жауап дайындалып жатыр...</p>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        <footer className="chat-composer">
          {attachedFiles.length > 0 && (
            <div className="attached-files">
              {attachedFiles.map((file) => (
                <span key={`${file.name}-${file.size}`}>
                  📎 {file.name}
                  <button type="button" onClick={() => removeFile(file.name)}>
                    ×
                  </button>
                </span>
              ))}
            </div>
          )}

          <div className="composer-row">
            <button
              type="button"
              className="attach-button"
              onClick={openFilePicker}
              title="Файл тіркеу"
            >
              +
            </button>

            <textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Сұрағыңызды жазыңыз..."
              rows={1}
            />

            <button
              type="button"
              className="send-button"
              onClick={sendMessage}
              disabled={(!input.trim() && attachedFiles.length === 0) || loading}
            >
              Жіберу
            </button>
          </div>
        </footer>
      </section>
    </section>
  );
}

function ChatMessage({ msg, initials }) {
  const isUser = msg.role === "user";

  return (
    <div className={`message ${isUser ? "user" : "assistant"}`}>
      {!isUser && <div className="bot-avatar">AI</div>}

      <div className="message-bubble">
        <p>{msg.content}</p>
        {msg.files?.length > 0 && (
          <div className="message-files">
            {msg.files.map((file) => (
              <span key={`${file.name}-${file.size}`}>📎 {file.name}</span>
            ))}
          </div>
        )}
        <small>{msg.time}</small>
      </div>

      {isUser && <div className="user-avatar">{initials || "ST"}</div>}
    </div>
  );
}

function ProfilePage({
  profile,
  setPage,
  stats,
  statsLoading,
  statsError,
}) {
  const rows = [
    ["ФИО", profile.full_name],
    ["Email", profile.email],
    ["Топ", profile.group],
    ["Мамандық", profile.specialty],
    ["Student ID", profile.student_id],
    ["Университет", profile.university],
  ];

  const courseStats =
    (stats || []).find((entry) => entry.course_id === COURSE_ID) ||
    (stats || [])[0] ||
    null;

  const totalPercent = courseStats?.overall_progress ?? 0;
  const scoreText =
    courseStats?.average_quiz_score === null || courseStats?.average_quiz_score === undefined
      ? "—"
      : `${courseStats.average_quiz_score}%`;

  return (
    <section className="page-shell profile-page-shell">
      <div className="profile-page-header">
        <div>
          <p className="profile-overline">Профиль</p>
          <h1>Профиль және оқу прогресі</h1>
          <p></p>
        </div>
      </div>

      {statsLoading && <p className="course-status">Статистика жүктеліп жатыр...</p>}
      {!statsLoading && statsError && (
        <p className="course-status course-status-error">{statsError}</p>
      )}

      <div className="profile-dashboard-grid">
        <article className="student-profile-card">
          <div className="student-profile-card__head">
            <div className="profile-avatar">{getInitials(profile.full_name)}</div>
            <div>
              <h2>{profile.full_name || "Студент"}</h2>
              <p>{profile.email || "email енгізілмеген"}</p>
            </div>
          </div>

          <div className="student-profile-table">
            {rows.slice(2).map(([label, value]) => (
              <div key={label}>
                <span>{label}</span>
                <strong>{value || "—"}</strong>
              </div>
            ))}
          </div>

          <button type="button" onClick={() => setPage("course")}>
            Оқуды жалғастыру
          </button>
        </article>

        <article className="profile-metric-card profile-metric-card--blue">
          <span>Жалпы прогресс</span>
          <strong>{totalPercent}%</strong>
          <div className="profile-metric-bar">
            <i style={{ width: `${totalPercent}%` }} />
          </div>
        </article>

        <article className="profile-metric-card profile-metric-card--green">
          <span>Орташа балл</span>
          <strong>{scoreText}</strong>
          <p>
            {courseStats?.total_quizz_attempts
              ? `${courseStats.total_quizz_attempts} рет тест тапсырылды`
              : "Quiz нәтижесі жоқ"}
          </p>
        </article>

        <article className="profile-metric-card profile-metric-card--plain">
          <span>Курс бойынша</span>
          <strong>
            {courseStats?.completed_modules ?? 0}/{courseStats?.total_modules ?? 0}
          </strong>
          <p>Аяқталған модульдер</p>
        </article>

        <article className="profile-metric-card profile-metric-card--plain">
          <span>Курс бойынша</span>
          <strong>{courseStats?.completed_quizzes ?? 0}/{courseStats?.total_quizzes ?? 0}</strong>
          <p>Аяқталған тесттер</p>
        </article>
      </div>

      <article className="profile-progress-panel">
        <div className="profile-progress-panel__title">
          <h2>Модульдер бойынша прогресс</h2>
          <span>{totalPercent}%</span>
        </div>

        <div className="profile-progress-list">
          {(courseStats?.modules || []).map((module) => (
            <div className="profile-module-row" key={module.module_id}>
              <b>{module.module_name}</b>
              <div className="profile-module-track">
                <i
                  className={module.module_progress === 100 ? "is-complete" : ""}
                  style={{ width: `${module.module_progress}%` }}
                />
              </div>
              <strong>{module.module_progress}%</strong>
            </div>
          ))}
        </div>
      </article>
    </section>
  );
}

function LoginPage({ setPage, setAuth, saveProfile, setCourseProgress }) {
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const canSubmit = useMemo(() => form.email.trim() && form.password.trim(), [form]);

  const login = async () => {
    setError("");
    try {
      const response = await fetch(`${API_BASE_URL}/api/users/login/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || data.error || "Login қатесі");

      localStorage.setItem("access", data.access || "local-access");
      localStorage.setItem("refresh", data.refresh || "local-refresh");
      setAuth({
        access: data.access || "local-access",
        refresh: data.refresh || "local-refresh",
      });

      const savedProfile = loadJSON("studentProfile", DEFAULT_PROFILE);
      const nextProfile = {
        ...savedProfile,
        ...data,
        email: data.email || form.email,
      };

      saveProfile(nextProfile);
      localStorage.setItem("currentUserEmail", nextProfile.email);

      const existingProgress = loadProgressForEmail(nextProfile.email);
      const legacyProgress =
        savedProfile.email === nextProfile.email
          ? loadJSON("courseProgress", {})
          : {};

      const progressToUse =
        Object.keys(existingProgress).length > 0 ? existingProgress : legacyProgress;

      setCourseProgress(progressToUse);
      saveProgressForEmail(nextProfile.email, progressToUse);

      setPage("home");
    } catch (errorObject) {
      const savedProfile = loadJSON("studentProfile", null);
      if (savedProfile && savedProfile.email === form.email) {
        localStorage.setItem("registeredLocal", "true");
        localStorage.setItem("access", "local-access");
        localStorage.setItem("refresh", "local-refresh");
        setAuth({ access: "local-access", refresh: "local-refresh" });
        localStorage.setItem("currentUserEmail", savedProfile.email);

        const savedProgress = loadProgressForEmail(savedProfile.email);
        setCourseProgress(savedProgress);

        setPage("home");
        return;
      }
      setError(errorObject.message);
    }
  };

  return (
    <AuthScreen title="Жүйеге кіру" subtitle="Тіркелген email және құпиясөзді енгізіңіз">
      <input
        placeholder="Email"
        value={form.email}
        onChange={(event) => setForm({ ...form, email: event.target.value })}
      />
      <input
        placeholder="Құпиясөз"
        type="password"
        value={form.password}
        onChange={(event) => setForm({ ...form, password: event.target.value })}
      />
      <button type="button" onClick={login} disabled={!canSubmit}>
        Кіру
      </button>
      <button className="link-button" type="button" onClick={() => setPage("register")}>
        Тіркелу
      </button>
      {error && <p className="form-error">{error}</p>}
    </AuthScreen>
  );
}

function RegisterPage({ setPage, setAuth, saveProfile, setCourseProgress }) {
  const [form, setForm] = useState({
    username: "",
    full_name: "",
    email: "",
    university: "ҚазҰМУ",
    faculty: "",
    group: "",
    role: "STUDENT",
    password: "",
  });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const canSubmit = useMemo(
    () =>
      form.username.trim() &&
      form.full_name.trim() &&
      form.email.trim() &&
      form.university.trim() &&
      form.faculty.trim() &&
      form.group.trim() &&
      form.password.trim(),
    [form]
  );

  const update = (key, value) => setForm((prev) => ({ ...prev, [key]: value }));

  const register = async () => {
    setError("");
    setSubmitting(true);

    try {
      const registerResponse = await fetch(`${API_BASE_URL}/api/users/register/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      const registerData = await registerResponse.json().catch(() => ({}));

      if (!registerResponse.ok) {
        throw new Error(
          registerData.detail || registerData.error || "Тіркелу қатесі."
        );
      }

      const loginResponse = await fetch(`${API_BASE_URL}/api/users/login/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: form.email,
          password: form.password,
        }),
      });
      const loginData = await loginResponse.json().catch(() => ({}));

      if (!loginResponse.ok) {
        throw new Error(
          loginData.detail || loginData.error || "Тіркелгеннен кейін кіру қатесі."
        );
      }

      localStorage.setItem("access", loginData.access);
      localStorage.setItem("refresh", loginData.refresh);
      setAuth({
        access: loginData.access,
        refresh: loginData.refresh,
      });

      const newProfile = {
        ...DEFAULT_PROFILE,
        full_name: form.full_name,
        email: form.email,
        university: form.university,
        specialty: form.faculty,
        group: form.group,
        role: form.role,
      };

      saveProfile(newProfile);
      localStorage.setItem("currentUserEmail", newProfile.email);
      setCourseProgress({});
      saveProgressForEmail(newProfile.email, {});

      setPage("home");
    } catch (errorObject) {
      setError(errorObject.message);
    } finally {
      setSubmitting(false);
    }
  };


  return (
    <AuthScreen title="Тіркелу" subtitle="Студент деректерін толық енгізіңіз">
      <input
        placeholder="Username"
        value={form.username}
        onChange={(event) => update("username", event.target.value)}
      />
      <input
        placeholder="ФИО"
        value={form.full_name}
        onChange={(event) => update("full_name", event.target.value)}
      />
      <input
        placeholder="Email"
        value={form.email}
        onChange={(event) => update("email", event.target.value)}
      />
      <input
        placeholder="Университет"
        value={form.university}
        onChange={(event) => update("university", event.target.value)}
      />
      <input
        placeholder="Факультет"
        value={form.faculty}
        onChange={(event) => update("faculty", event.target.value)}
      />
      <input
        placeholder="Группа"
        value={form.group}
        onChange={(event) => update("group", event.target.value)}
      />
      <input
        placeholder="Құпиясөз"
        type="password"
        value={form.password}
        onChange={(event) => update("password", event.target.value)}
      />
      <button type="button" onClick={register} disabled={!canSubmit || submitting}>
        {submitting ? "Тіркелуде..." : "Тіркелу және кіру"}
      </button>
      <button className="link-button" type="button" onClick={() => setPage("login")}>
        Login бетіне өту
      </button>
      {error && <p className="form-error">{error}</p>}
    </AuthScreen>
  );
}

function AuthScreen({ title, subtitle, children }) {
  return (
    <div className="auth-screen">
      <div className="auth-card">
        <div className="auth-brand">
          <strong>BioStat</strong>
          <span>ҚазҰМУ</span>
        </div>
        <h1>{title}</h1>
        <p>{subtitle}</p>
        <div className="auth-form">{children}</div>
      </div>
    </div>
  );
}


export default App;
