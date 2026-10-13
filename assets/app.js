// AI 동아리 앱 갤러리 공통 스크립트
// 사이트가 읽는 데이터는 data/projects.json 하나뿐이다 (SPEC 5-1).
// 경로는 모두 상대 경로로 써서 joonssem.github.io/ai-club-2026/ 아래에서도 그대로 작동하게 한다.

(function () {
  "use strict";

  const DATA_URL = "../data/projects.json";

  function el(tag, attrs, children) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(attrs || {})) {
      if (value === undefined || value === null || value === false) continue;
      if (key === "text") node.textContent = value;
      else node.setAttribute(key, value === true ? "" : value);
    }
    for (const child of [].concat(children || [])) {
      if (child) node.append(child);
    }
    return node;
  }

  async function loadProjects() {
    const res = await fetch(DATA_URL, { cache: "no-cache" });
    if (!res.ok) throw new Error("projects.json " + res.status);
    return res.json();
  }

  // 팀 이름이 아직 없으면 "1팀"처럼 보여 준다.
  function teamLabel(project) {
    if (project.teamName) return project.teamName;
    const n = String(project.id || "").replace(/\D/g, "");
    return n ? n + "팀" : "팀";
  }

  function appHref(project) {
    return "../apps/" + encodeURIComponent(project.id) + "/index.html";
  }

  function showError(container, message) {
    container.replaceChildren(el("p", { class: "notice", role: "alert", text: message }));
  }

  // ---------- 갤러리 ----------

  function buildCard(project) {
    const status = project.status || "waiting";
    const team = teamLabel(project);

    if (status === "waiting") {
      return el("article", { class: "card" }, [
        el("div", { class: "card-thumb placeholder", "aria-hidden": "true" }),
        el("div", { class: "card-body" }, [
          el("h3", { class: "card-title", text: team }),
          el("div", { class: "card-badges" }, el("span", { class: "badge", text: "준비 중" })),
          el("p", { class: "card-tagline notice", text: "2주차 발표 뒤에 작품이 올라와요." })
        ])
      ]);
    }

    const appName = project.appName || team;
    const thumb = el("img", {
      class: "card-thumb",
      src: "../apps/" + encodeURIComponent(project.id) + "/thumb.png",
      alt: appName + " 첫 화면",
      loading: "lazy"
    });
    // 썸네일이 아직 없으면 빈 칸으로 바꾼다.
    thumb.addEventListener("error", () => {
      thumb.replaceWith(el("div", { class: "card-thumb placeholder", "aria-hidden": "true" }));
    }, { once: true });

    const badges = el("div", { class: "card-badges" });
    if (status === "archived-partial") {
      badges.append(el("span", { class: "badge accent", text: "일부 기능은 원본에서만 작동" }));
    }
    if (status === "link-only") {
      badges.append(el("span", { class: "badge", text: "원본 링크만 있음" }));
    }

    const actions = el("div", { class: "card-actions" });
    if (status === "archived" || status === "archived-partial") {
      actions.append(el("a", {
        class: "btn primary", href: appHref(project), target: "_blank", rel: "noopener", text: "앱 실행"
      }));
    }
    if (project.sourceUrl && project.sourceOpen !== false) {
      actions.append(el("a", {
        class: "btn", href: project.sourceUrl, target: "_blank", rel: "noopener noreferrer", text: "Canva 원본"
      }));
    } else {
      actions.append(el("span", { class: "btn", "aria-disabled": "true", text: "원본 종료" }));
    }
    actions.append(el("a", {
      class: "btn", href: "project.html?team=" + encodeURIComponent(project.id), text: "기획서 보기"
    }));

    return el("article", { class: "card" }, [
      thumb,
      el("div", { class: "card-body" }, [
        el("p", { class: "card-team", text: team }),
        el("h3", { class: "card-title", text: appName }),
        project.tagline ? el("p", { class: "card-tagline", text: project.tagline }) : null,
        badges.childElementCount ? badges : null,
        actions
      ])
    ]);
  }

  async function renderGallery() {
    const container = document.getElementById("cards");
    try {
      const data = await loadProjects();
      const heading = document.getElementById("gallery-term");
      if (heading && data.club) heading.textContent = data.club + " 작품";
      container.replaceChildren(...(data.projects || []).map(buildCard));
      container.setAttribute("aria-busy", "false");
    } catch (err) {
      showError(container, "작품 목록을 불러오지 못했어요. 잠시 뒤 다시 열어 주세요.");
      console.error(err);
    }
  }

  // ---------- 기획서 보기 (발표 모드) ----------

  function buildSlides(project) {
    const features = (project.features || []).filter(Boolean);
    const open = project.status === "archived" || project.status === "archived-partial";
    return [
      { step: "01", heading: "어떤 불편을 풀었나요?",
        body: el("p", { class: "slide-text", text: project.problem || "아직 적지 않았어요." }) },
      { step: "02", heading: "누가 쓰나요?",
        body: el("p", { class: "slide-text", text: project.user || project.tagline || "아직 적지 않았어요." }) },
      { step: "03", heading: "기능 3개",
        body: features.length
          ? el("ol", { class: "slide-list" }, features.map((f) => el("li", { text: f })))
          : el("p", { class: "slide-text", text: "아직 적지 않았어요." }) },
      { step: "04", heading: "이렇게 되면 완성!",
        body: el("div", {}, [
          el("p", { class: "slide-text", text: project.testSentence || "아직 적지 않았어요." }),
          open ? el("p", {}, el("a", {
            class: "btn primary", href: appHref(project), target: "_blank", rel: "noopener", text: "앱 실행"
          })) : null,
          // link-only는 보관본이 없으므로, 원본이 열려 있으면 원본으로 시연한다 (SPEC 4-3)
          !open && project.sourceUrl && project.sourceOpen !== false ? el("p", {}, el("a", {
            class: "btn primary", href: project.sourceUrl, target: "_blank", rel: "noopener noreferrer", text: "Canva 원본"
          })) : null
        ]) }
    ];
  }

  async function renderProject() {
    const stage = document.getElementById("slide");
    const title = document.getElementById("project-title");
    const prev = document.getElementById("prev");
    const next = document.getElementById("next");
    const count = document.getElementById("count");
    const teamId = new URLSearchParams(location.search).get("team");

    let project;
    try {
      const data = await loadProjects();
      project = (data.projects || []).find((p) => p.id === teamId);
    } catch (err) {
      console.error(err);
      showError(stage, "기획서를 불러오지 못했어요.");
      return;
    }
    if (!project) {
      showError(stage, "어떤 팀의 기획서인지 찾지 못했어요. 갤러리에서 다시 골라 주세요.");
      return;
    }

    const team = teamLabel(project);
    title.textContent = project.appName ? team + " · " + project.appName : team;
    document.title = title.textContent + " 기획서 | AI 동아리 갤러리";

    if (project.status === "waiting") {
      showError(stage, "아직 준비 중이에요. 2주차 발표 뒤에 기획서가 올라와요.");
      return;
    }

    const slides = buildSlides(project);
    let index = 0;

    function show(i) {
      index = Math.max(0, Math.min(slides.length - 1, i));
      const s = slides[index];
      stage.replaceChildren(
        el("p", { class: "slide-step", text: s.step }),
        el("h2", { class: "slide-heading", text: s.heading }),
        s.body
      );
      prev.disabled = index === 0;
      next.disabled = index === slides.length - 1;
      count.textContent = (index + 1) + " / " + slides.length;
    }

    prev.addEventListener("click", () => show(index - 1));
    next.addEventListener("click", () => show(index + 1));
    document.addEventListener("keydown", (e) => {
      if (e.key === "ArrowLeft" || e.key === "PageUp") show(index - 1);
      if (e.key === "ArrowRight" || e.key === "PageDown" || e.key === " ") {
        e.preventDefault();
        show(index + 1);
      }
    });
    document.getElementById("slide-nav").hidden = false;
    show(0);
  }

  // ---------- 활동 안내 ----------

  // 기획서 앱 QR (교실 화면에 띄워 아이패드로 찍을 수 있게). 라이브러리가 없으면 링크 버튼만 남는다.
  function renderHome() {
    const link = document.getElementById("plan-app-link");
    const box = document.getElementById("plan-app-qr");
    if (!link || !box || typeof window.qrcode !== "function") return;
    const qr = window.qrcode(0, "M");
    qr.addData(link.href);
    qr.make();
    box.innerHTML = qr.createSvgTag({ cellSize: 4, margin: 2, scalable: true });
  }

  const page = document.body.dataset.page;
  if (page === "home") renderHome();
  if (page === "gallery") renderGallery();
  if (page === "project") renderProject();
})();
