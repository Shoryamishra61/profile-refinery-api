(() => {
  "use strict";

  const form = document.querySelector("#extraction-form");
  const urlsInput = document.querySelector("#profile-urls");
  const liAtInput = document.querySelector("#li-at");
  const jsessionInput = document.querySelector("#jsessionid");
  const companionInput = document.querySelector("#companion-cookies");
  const userAgentInput = document.querySelector("#user-agent");
  const languageInput = document.querySelector("#accept-language");
  const submitButton = document.querySelector("#extract-button");
  const actionTitle = document.querySelector("#action-title");
  const actionDetail = document.querySelector("#action-detail");
  const formError = document.querySelector("#form-error");
  const resultsSection = document.querySelector("#results");
  const resultList = document.querySelector("#result-list");
  const runSummary = document.querySelector("#run-summary");
  const urlCount = document.querySelector("#url-count");
  const cardDialog = document.querySelector("#profile-card-dialog");
  const cardCanvas = document.querySelector("#profile-card-canvas");
  const cardPosition = document.querySelector("#card-position");
  const extractionProgress = document.querySelector("#extraction-progress");
  const progressMessage = document.querySelector("#progress-message");
  const progressTime = document.querySelector("#progress-time");
  const urlValidation = document.querySelector("#url-validation");
  let latestResponse = null;
  let currentCardIndex = 0;
  let progressTimer = null;

  userAgentInput.value = navigator.userAgent;

  const profileUrls = () => urlsInput.value
    .split(/\r?\n/)
    .map((value) => value.trim())
    .filter(Boolean);

  const validateProfileUrl = (rawValue) => {
    const raw = String(rawValue || "").trim();
    if (!raw) return "A LinkedIn profile URL is required.";
    const normalized = /^(?:www\.)?linkedin\.com\//i.test(raw) ? `https://${raw}` : raw;
    let parsed;
    try {
      parsed = new URL(normalized);
    } catch {
      return "The URL is malformed.";
    }
    if (parsed.protocol !== "https:") return "Only HTTPS URLs are accepted.";
    if (parsed.username || parsed.password || (parsed.port && parsed.port !== "443")) {
      return "Credentials and non-standard ports are not allowed.";
    }
    if (!["linkedin.com", "www.linkedin.com"].includes(parsed.hostname.toLowerCase())) {
      return "Only linkedin.com member-profile URLs are accepted.";
    }
    if (parsed.hash) return "URL fragments are not accepted.";
    let decodedPath;
    try {
      decodedPath = decodeURIComponent(parsed.pathname);
    } catch {
      return "The profile path contains invalid encoding.";
    }
    const segments = decodedPath.split("/").filter(Boolean);
    const validSlug = /^[A-Za-z0-9](?:[A-Za-z0-9_-]{0,98}[A-Za-z0-9])?$/;
    if (segments.length !== 2 || segments[0] !== "in" || !validSlug.test(segments[1])) {
      return "Expected a member URL shaped as linkedin.com/in/vanity-slug.";
    }
    if (decodedPath.includes("..") || /[\\@:]/.test(decodedPath)) {
      return "The profile path contains prohibited characters.";
    }
    return null;
  };

  const validateProfileUrls = () => profileUrls().map((url, index) => ({
    line: index + 1,
    url,
    error: validateProfileUrl(url),
  }));

  const renderUrlValidation = () => {
    const checks = validateProfileUrls();
    urlCount.textContent = `${checks.length} / 10`;
    const invalid = checks.filter((item) => item.error);
    urlsInput.setAttribute("aria-invalid", invalid.length ? "true" : "false");
    if (!checks.length) {
      urlValidation.textContent = "";
      urlValidation.className = "url-validation";
    } else if (invalid.length) {
      urlValidation.className = "url-validation invalid";
      urlValidation.innerHTML = `<strong>${invalid.length} URL${invalid.length === 1 ? " needs" : "s need"} attention</strong><ul>${invalid.map((item) => `<li>Line ${item.line}: ${escapeHtml(item.error)}</li>`).join("")}</ul>`;
    } else {
      urlValidation.className = "url-validation valid";
      urlValidation.textContent = `${checks.length} valid LinkedIn profile URL${checks.length === 1 ? "" : "s"}.`;
    }
    return invalid;
  };

  urlsInput.addEventListener("input", renderUrlValidation);

  document.querySelectorAll("[data-reveal]").forEach((button) => {
    button.addEventListener("click", () => {
      const target = document.getElementById(button.dataset.reveal);
      const revealed = target.type === "text";
      target.type = revealed ? "password" : "text";
      button.textContent = revealed ? "SHOW" : "HIDE";
      button.setAttribute("aria-label", `${revealed ? "Show" : "Hide"} secret value`);
    });
  });

  const escapeHtml = (value) => String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

  const fieldValue = (profile, key, fallback = "—") => {
    const field = profile?.profile?.[key];
    return field?.value ?? fallback;
  };

  const countField = (profile, key) => {
    const field = profile?.profile?.[key];
    return Array.isArray(field?.value) ? field.value.length : "—";
  };

  const safeHttpsUrl = (value) => {
    try {
      const url = new URL(String(value || ""));
      return url.protocol === "https:" ? url.href : "";
    } catch {
      return "";
    }
  };

  const normalizeMediaUrl = (value) => safeHttpsUrl(
    String(value || "").replaceAll("&amp;", "&").replaceAll("\\_", "_")
  );

  const mediaProxyUrl = (value) => {
    const source = normalizeMediaUrl(value);
    return source ? `${location.origin}/v1/profile-media?url=${encodeURIComponent(source)}` : "";
  };

  const formatObserved = (value) => {
    const date = new Date(value || "");
    return Number.isNaN(date.valueOf())
      ? "Observation time unavailable"
      : `Observed ${new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date)}`;
  };

  const formatDateValue = (value) => {
    if (!value?.year) return "";
    if (!value.month) return String(value.year);
    return new Intl.DateTimeFormat(undefined, { month: "short", year: "numeric" })
      .format(new Date(value.year, value.month - 1, 1));
  };

  const formatDateRange = (item) => {
    const start = formatDateValue(item?.start_date);
    const end = item?.is_current ? "Present" : formatDateValue(item?.end_date);
    return [start, end].filter(Boolean).join(" – ");
  };

  const urlSlug = (value, segment) => {
    const url = safeHttpsUrl(value);
    if (!url) return "";
    const parts = new URL(url).pathname.split("/").filter(Boolean);
    const index = parts.indexOf(segment);
    return index >= 0 ? parts[index + 1] || "" : "";
  };

  const profileCardMarkup = (profile) => {
    const name = fieldValue(profile, "name", "Unnamed profile");
    const identity = fieldValue(profile, "identity", {});
    const slug = identity?.vanity_slug || identity?.public_identifier || "profile";
    const headline = fieldValue(profile, "headline", "Headline not provided");
    const location = fieldValue(profile, "location", "Location not provided");
    const about = fieldValue(profile, "about", "About section not provided by the upstream profile.");
    const imageUrl = normalizeMediaUrl(fieldValue(profile, "profile_image", {})?.url);
    const renderedImageUrl = mediaProxyUrl(imageUrl);
    const canonicalUrl = safeHttpsUrl(profile?.canonical_url);
    const experience = fieldValue(profile, "experience", []);
    const education = fieldValue(profile, "education", []);
    const skills = fieldValue(profile, "skills", []);
    const certifications = fieldValue(profile, "certifications", []);
    const languages = fieldValue(profile, "languages", []);
    const initial = String(name).trim().charAt(0).toUpperCase() || "P";

    const fieldMarkup = (fields) => {
      const available = fields.filter((field) => field.value !== null && field.value !== undefined && field.value !== "");
      if (!available.length) return "";
      return `<dl class="passport-fields">${available.map((field) => {
        const safeLink = field.link ? safeHttpsUrl(field.link) : "";
        const value = escapeHtml(field.display || field.value);
        return `<div><dt>${escapeHtml(field.label)}</dt><dd>${safeLink ? `<a href="${escapeHtml(safeLink)}" target="_blank" rel="noopener noreferrer">${value}</a>` : value}</dd></div>`;
      }).join("")}</dl>`;
    };

    const entries = (title, values, renderer, open = true) => {
      const rows = Array.isArray(values) ? values.map(renderer).filter(Boolean) : [];
      const content = rows.length
        ? rows.map((row) => `<article class="passport-entry"><strong>${escapeHtml(row.title)}</strong>${row.meta ? `<p class="passport-entry-meta">${escapeHtml(row.meta)}</p>` : ""}${fieldMarkup(row.fields || [])}${row.description ? `<p class="passport-entry-description">${escapeHtml(row.description)}</p>` : ""}</article>`).join("")
        : '<p class="passport-empty">No upstream evidence returned for this section.</p>';
      return `<details class="passport-section"${open ? " open" : ""}><summary>${escapeHtml(title)} <span>${rows.length}</span></summary><div class="passport-section-content">${content}</div></details>`;
    };

    const overviewRows = entries("Identity & overview", [{
      title: name,
      meta: headline,
      description: about,
      fields: [
        { label: "First name", value: fieldValue(profile, "first_name", "") },
        { label: "Last name", value: fieldValue(profile, "last_name", "") },
        { label: "Location", value: fieldValue(profile, "location", "") },
        { label: "Profile slug", value: slug },
        { label: "Public identifier", value: identity?.public_identifier || "" },
        { label: "Member URN", value: identity?.member_urn || "" },
        { label: "Canonical profile", value: canonicalUrl, link: canonicalUrl },
        { label: "Profile image", value: imageUrl, display: "Open original image", link: imageUrl },
        { label: "Background image", value: normalizeMediaUrl(fieldValue(profile, "background_image", {})?.url), display: "Open original image", link: normalizeMediaUrl(fieldValue(profile, "background_image", {})?.url) },
      ],
    }], (item) => item);
    const experienceRows = entries("Experience", experience, (item) => {
      const dates = formatDateRange(item);
      return {
        title: item.title || item.company_name || "Role",
        meta: [item.company_name, dates].filter(Boolean).join(" · "),
        description: item.description || "",
        fields: [
          { label: "Company", value: item.company_name },
          { label: "Employment type", value: item.employment_type },
          { label: "Date range", value: dates },
          { label: "Duration", value: item.duration },
          { label: "Location", value: item.location },
          { label: "Workplace type", value: item.workplace_type },
          { label: "Company URL", value: item.company_url, link: item.company_url },
          { label: "Company URN", value: item.company_urn },
        ],
      };
    });
    const educationRows = entries("Education", education, (item) => ({
      title: item.school_name || "Education",
      meta: [item.degree_name, item.field_of_study, formatDateRange(item)].filter(Boolean).join(" · "),
      description: item.description || "",
      fields: [
        { label: "School", value: item.school_name },
        { label: "Degree", value: item.degree_name },
        { label: "Field of study", value: item.field_of_study },
        { label: "Date range", value: formatDateRange(item) },
        { label: "Grade", value: item.grade },
        { label: "Activities", value: item.activities },
        { label: "School URL", value: item.school_url, link: item.school_url },
        { label: "School URN", value: item.school_urn },
      ],
    }));
    const skillRows = entries("Skills", skills, (item) => ({
      title: item.name || "",
      fields: [{ label: "Entity ID", value: item.id }],
    }));
    const certificationRows = entries("Certifications", certifications, (item) => ({
      title: item.name || "",
      meta: item.authority || "",
      fields: [
        { label: "Issuing authority", value: item.authority },
        { label: "Credential ID", value: item.license_number },
        { label: "Issued", value: formatDateValue(item.start_date) },
        { label: "Expires", value: formatDateValue(item.end_date) },
        { label: "Credential URL", value: item.credential_url, link: item.credential_url },
        { label: "Entity ID", value: item.id },
      ],
    }));
    const languageRows = entries("Languages", languages, (item) => ({
      title: item.name || "",
      fields: [
        { label: "Proficiency", value: item.proficiency },
        { label: "Entity ID", value: item.id },
      ],
    }));
    const avatar = `<div class="passport-avatar-shell">
      <div class="passport-avatar passport-avatar-fallback" aria-hidden="${imageUrl ? "true" : "false"}">${escapeHtml(initial)}</div>
      ${renderedImageUrl ? `<img class="passport-avatar" src="${escapeHtml(renderedImageUrl)}" alt="${escapeHtml(name)} profile photo" decoding="async">` : ""}
    </div>`;

    return `<article class="profile-passport" tabindex="0" aria-label="Profile card for ${escapeHtml(name)}">
      <section class="passport-identity">
        <p class="passport-kicker">${escapeHtml(String(profile?.retrieval?.mode || "live").toUpperCase())} PROFILE</p>
        ${avatar}
        <h3>${escapeHtml(name)}</h3>
        <p class="passport-slug">linkedin.com/in/${escapeHtml(slug)}</p>
        <p class="passport-headline">${escapeHtml(headline)}</p>
        <p class="passport-location"><span>Location</span>${escapeHtml(location)}</p>
        ${canonicalUrl ? `<a class="passport-profile-link" href="${escapeHtml(canonicalUrl)}" target="_blank" rel="noopener noreferrer">View source profile</a>` : ""}
      </section>
      <section class="passport-data">
        <div class="passport-summary" aria-label="Profile section counts">
          <div class="passport-metric"><strong>${countField(profile, "experience")}</strong><span>Experience</span></div>
          <div class="passport-metric"><strong>${countField(profile, "education")}</strong><span>Education</span></div>
          <div class="passport-metric"><strong>${countField(profile, "skills")}</strong><span>Skills</span></div>
          <div class="passport-metric"><strong>${countField(profile, "certifications")}</strong><span>Credentials</span></div>
          <div class="passport-metric"><strong>${countField(profile, "languages")}</strong><span>Languages</span></div>
        </div>
        <p class="passport-about">All returned sections are expanded below. Scroll this panel to inspect every observed field.</p>
        <div class="passport-sections">${overviewRows}${experienceRows}${educationRows}${skillRows}${certificationRows}${languageRows}</div>
        <p class="passport-observed">${escapeHtml(formatObserved(profile?.observed_at))} · Missing values remain missing.</p>
      </section>
    </article>`;
  };

  const successfulProfiles = () => (latestResponse?.results || [])
    .filter((result) => result.profile)
    .map((result) => result.profile);

  const showProfileCard = (index) => {
    const profiles = successfulProfiles();
    if (!profiles.length) return;
    currentCardIndex = (index + profiles.length) % profiles.length;
    cardCanvas.innerHTML = profileCardMarkup(profiles[currentCardIndex]);
    cardPosition.textContent = `${currentCardIndex + 1} / ${profiles.length}`;
    document.querySelector("#previous-profile-card").disabled = profiles.length < 2;
    document.querySelector("#next-profile-card").disabled = profiles.length < 2;
    if (!cardDialog.open) cardDialog.showModal();
    cardCanvas.querySelector(".profile-passport")?.focus({ preventScroll: true });
  };

  const standaloneCardDocument = (profile) => `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>${escapeHtml(fieldValue(profile, "name", "Profile"))} · Profile card</title>
<style>${document.querySelector("#standalone-card-styles")?.textContent || `
*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;padding:24px;color:#f7f4ea;background:radial-gradient(circle at 15% 10%,#415bc0,#0d1224 58%);font-family:Arial,sans-serif}.profile-passport{width:min(1100px,100%);display:grid;grid-template-columns:minmax(250px,.65fr) minmax(0,1.35fr);border:1px solid #ffffffb8;border-radius:28px;overflow:hidden;background:linear-gradient(145deg,#1f2a4f,#0e1327);box-shadow:0 38px 90px #0008}.passport-identity,.passport-data{padding:32px}.passport-identity{display:flex;flex-direction:column;border-right:1px solid #ffffff2e;background:linear-gradient(180deg,#1755e861,transparent 54%)}.passport-kicker,.passport-slug,.passport-location span,.passport-observed{font:700 11px monospace;text-transform:uppercase;letter-spacing:.08em;color:#d9ff43}.passport-avatar{width:148px;height:148px;margin:28px 0 20px;border:4px solid #fff;border-radius:50%;object-fit:cover}.passport-avatar-fallback{display:grid;place-items:center;color:#141412;background:#d9ff43;font:64px Georgia}.passport-identity h3{margin:0;font:56px/.92 Georgia}.passport-slug{color:#9eb9ff;text-transform:none}.passport-headline{line-height:1.45}.passport-location{margin-top:auto;padding-top:20px;border-top:1px solid #ffffff38}.passport-location span{display:block;margin-bottom:5px}.passport-profile-link{color:white}.passport-data{display:flex;flex-direction:column;gap:18px}.passport-summary{display:grid;grid-template-columns:repeat(5,1fr);border:1px solid #ffffff2e;border-radius:16px;overflow:hidden}.passport-metric{padding:12px 6px;border-right:1px solid #ffffff29;text-align:center}.passport-metric:last-child{border:0}.passport-metric strong{display:block;color:#d9ff43;font:28px Georgia}.passport-metric span{font:9px monospace;text-transform:uppercase}.passport-about{color:#d8d9e2}.passport-sections{display:grid;gap:10px}.passport-section{border:1px solid #ffffff2e;border-radius:12px}.passport-section summary{display:flex;justify-content:space-between;padding:12px 16px;font:700 11px monospace;text-transform:uppercase;cursor:pointer}.passport-section summary span{color:#d9ff43}.passport-section-content{display:grid;gap:8px;padding:0 16px 16px}.passport-entry{padding:12px;border-left:3px solid #1755e8;background:#ffffff0f}.passport-entry strong{display:block}.passport-entry-meta,.passport-entry-description,.passport-empty{color:#b9bfd0;font-size:12px}.passport-entry-description{white-space:pre-line}.passport-fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px 16px;margin-top:12px}.passport-fields dt{color:#858ea7;font:700 9px monospace;text-transform:uppercase}.passport-fields dd{margin:2px 0 0;font-size:12px;overflow-wrap:anywhere}.passport-fields a{color:#a9c0ff}@media(max-width:720px){body{padding:0}.profile-passport{grid-template-columns:1fr;border-radius:0}.passport-identity{border-right:0;border-bottom:1px solid #ffffff2e}.passport-summary{grid-template-columns:repeat(3,1fr)}.passport-fields{grid-template-columns:1fr}}`}</style></head><body>${profileCardMarkup(profile)}</body></html>`;

  const flatten = (result) => {
    const profile = result.profile;
    const experience = fieldValue(profile, "experience", []);
    const education = fieldValue(profile, "education", []);
    const skills = fieldValue(profile, "skills", []);
    const certifications = fieldValue(profile, "certifications", []);
    const languages = fieldValue(profile, "languages", []);
    const identity = fieldValue(profile, "identity", {});
    const current = Array.isArray(experience) ? experience.find((item) => item.is_current) || experience[0] : null;
    const previous = Array.isArray(experience) ? experience.find((item) => item !== current) : null;
    const school = Array.isArray(education) ? education[0] : null;
    return {
      status: result.status,
      errorCode: result.error?.code || "",
      profileUrl: profile?.canonical_url || result.input_url,
      firstName: fieldValue(profile, "first_name", ""),
      lastName: fieldValue(profile, "last_name", ""),
      linkedinHeadline: fieldValue(profile, "headline", ""),
      location: fieldValue(profile, "location", ""),
      linkedinDescription: fieldValue(profile, "about", ""),
      linkedinProfileSlug: identity?.vanity_slug || "",
      linkedinProfileUrn: identity?.member_urn || "",
      linkedinProfileId: identity?.public_identifier || "",
      linkedinProfileImageUrl: fieldValue(profile, "profile_image", {})?.url || "",
      linkedinProfileImageUrn: fieldValue(profile, "profile_image", {})?.artifact_id || "",
      linkedinBackgroundImageUrl: fieldValue(profile, "background_image", {})?.url || "",
      linkedinBackgroundImageUrn: fieldValue(profile, "background_image", {})?.artifact_id || "",
      companyName: current?.company_name || "",
      companyIndustry: "",
      companyWebsite: "",
      connectionDegree: "",
      connectionsUrl: "",
      linkedinCompanyUrl: current?.company_url || "",
      linkedinCompanySlug: urlSlug(current?.company_url, "company"),
      linkedinJobTitle: current?.title || "",
      linkedinJobDateRange: formatDateRange(current),
      linkedinJobLocation: current?.location || "",
      linkedinJobDescription: current?.description || "",
      previousCompanyName: previous?.company_name || "",
      linkedinPreviousCompanyUrl: previous?.company_url || "",
      linkedinPreviousCompanySlug: urlSlug(previous?.company_url, "company"),
      linkedinPreviousJobTitle: previous?.title || "",
      linkedinPreviousJobDateRange: formatDateRange(previous),
      linkedinPreviousJobLocation: previous?.location || "",
      linkedinPreviousJobDescription: previous?.description || "",
      linkedinSchoolName: school?.school_name || "",
      linkedinSchoolUrl: school?.school_url || "",
      linkedinSchoolCompanySlug: urlSlug(school?.school_url, "school"),
      linkedinSchoolDateRange: formatDateRange(school),
      linkedinSchoolDegree: school?.degree_name || "",
      linkedinSchoolFieldOfStudy: school?.field_of_study || "",
      linkedinSchoolDescription: school?.description || "",
      linkedinSkillsLabel: Array.isArray(skills) ? skills.map((item) => item.name).join(" | ") : "",
      certifications: Array.isArray(certifications) ? certifications.map((item) => item.name).join(" | ") : "",
      languages: Array.isArray(languages) ? languages.map((item) => item.name).join(" | ") : "",
      linkedinConnectionsCount: "",
      linkedinFollowersCount: "",
      linkedinIsHiringBadge: "",
      linkedinIsOpenToWorkBadge: "",
      mutualConnectionsUrl: "",
      professionalEmail: "",
      refreshedAt: profile?.observed_at || "",
      evidenceMode: profile?.retrieval?.mode || "",
      partial: profile?.partial ?? "",
    };
  };

  const errorGuidance = (error) => {
    const guidance = {
      INVALID_PROFILE_URL: "Correct the URL and retry. No LinkedIn request was made for this item.",
      SESSION_EXPIRED: "Use a current LinkedIn session and retry only when you are authorized to do so.",
      FORBIDDEN: "LinkedIn rejected the authenticated request. Verify ordinary session access before retrying.",
      RATE_LIMITED: "Wait for the stated retry interval before making another request.",
      UPSTREAM_CHALLENGE: "LinkedIn presented an access challenge. This extractor will not bypass it.",
      UPSTREAM_CIRCUIT_OPEN: "Live extraction is temporarily paused after a proven upstream failure.",
      SCHEMA_CHANGED: "The upstream response could not be normalized safely; no missing values were invented.",
      UPSTREAM_UNAVAILABLE: "LinkedIn is temporarily unavailable. Retry later.",
      UPSTREAM_TIMEOUT: "The upstream request timed out. Retry later rather than submitting repeatedly.",
    };
    return guidance[error?.code] || "Review the typed error before retrying.";
  };

  const renderResults = (payload) => {
    const results = payload.results || [];
    const succeeded = results.filter((item) => item.status === "succeeded").length;
    const partial = results.filter((item) => item.status === "partial").length;
    const failed = results.filter((item) => item.status === "failed").length;
    runSummary.innerHTML = `
      <div class="metric"><span>Profiles</span><strong>${results.length}</strong></div>
      <div class="metric"><span>Succeeded</span><strong>${succeeded}</strong></div>
      <div class="metric"><span>Partial</span><strong>${partial}</strong></div>
      <div class="metric"><span>Failed / skipped</span><strong>${failed + results.filter((item) => item.status === "skipped").length}</strong></div>`;

    resultList.innerHTML = results.map((result, index) => {
      const profile = result.profile;
      const name = fieldValue(profile, "name", result.error?.title || "Not extracted");
      const className = result.status === "succeeded" ? "good" : result.status === "partial" ? "partial" : "failed";
      const operations = profile?.meta?.operations_succeeded?.join(" → ") || "No operation completed";
      const facts = profile ? `
        <div class="profile-facts">
          <div class="fact"><span>Headline</span><strong title="${escapeHtml(fieldValue(profile, "headline"))}">${escapeHtml(fieldValue(profile, "headline"))}</strong></div>
          <div class="fact"><span>Location</span><strong>${escapeHtml(fieldValue(profile, "location"))}</strong></div>
          <div class="fact"><span>Experience</span><strong>${countField(profile, "experience")}</strong></div>
          <div class="fact"><span>Education</span><strong>${countField(profile, "education")}</strong></div>
          <div class="fact"><span>Skills</span><strong>${countField(profile, "skills")}</strong></div>
          <div class="fact"><span>Certifications / languages</span><strong>${countField(profile, "certifications")} / ${countField(profile, "languages")}</strong></div>
        </div>` : `<div class="error-detail"><strong>${escapeHtml(result.error?.code || "FAILED")}</strong><p>${escapeHtml(result.error?.detail || "No profile data returned.")}</p><p>${escapeHtml(errorGuidance(result.error))}</p>${result.error?.retry_after_seconds ? `<p>Retry after ${escapeHtml(result.error.retry_after_seconds)} seconds.</p>` : ""}</div>`;
      return `<article class="result-card">
        <div class="result-index">${String(index + 1).padStart(2, "0")}</div>
        <div class="result-body">
          <div class="result-topline">
            <div><h3>${escapeHtml(name)}</h3><span class="result-url">${escapeHtml(profile?.canonical_url || result.input_url)}</span></div>
            <span class="result-status ${className}">${escapeHtml(result.status)}</span>
          </div>
          ${facts}
          ${profile ? `<div class="result-actions"><button class="view-card-button" type="button" data-profile-card="${index}">View immersive card</button></div>` : ""}
          <p class="operation-line">PROVENANCE / ${escapeHtml(profile?.retrieval?.mode || "none")} · ${escapeHtml(operations)}</p>
        </div>
      </article>`;
    }).join("");
    resultsSection.hidden = false;
    resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const download = (filename, content, type) => {
    const blob = new Blob([content], { type });
    const href = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = href;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(href);
  };

  const csvCell = (value) => {
    let safe = String(value ?? "");
    if (/^[=+\-@]/.test(safe)) safe = `'${safe}`;
    return `"${safe.replaceAll('"', '""')}"`;
  };

  const renderFormError = (title, details = []) => {
    formError.innerHTML = `<strong>${escapeHtml(title)}</strong>${details.length ? `<ul>${details.map((detail) => `<li>${escapeHtml(detail)}</li>`).join("")}</ul>` : ""}`;
    formError.hidden = false;
  };

  const startProgress = (count) => {
    const startedAt = Date.now();
    extractionProgress.hidden = false;
    form.setAttribute("aria-busy", "true");
    submitButton.disabled = true;
    submitButton.textContent = "Extracting profiles…";
    progressMessage.textContent = `Processing ${count} profile${count === 1 ? "" : "s"}. The server reports results only when the request completes.`;
    progressTime.textContent = "0s elapsed";
    progressTimer = window.setInterval(() => {
      progressTime.textContent = `${Math.floor((Date.now() - startedAt) / 1000)}s elapsed`;
    }, 1000);
  };

  const stopProgress = () => {
    if (progressTimer) window.clearInterval(progressTimer);
    progressTimer = null;
    extractionProgress.hidden = true;
    form.removeAttribute("aria-busy");
    submitButton.disabled = false;
    submitButton.textContent = "Extract profiles";
  };

  document.querySelector("#download-json").addEventListener("click", () => {
    if (latestResponse) download("profile-refinery-profiles.json", JSON.stringify(latestResponse, null, 2), "application/json");
  });
  document.querySelector("#download-csv").addEventListener("click", () => {
    if (!latestResponse) return;
    const rows = latestResponse.results.map(flatten);
    const headers = [...new Set(rows.flatMap((row) => Object.keys(row)))];
    const csv = [headers.map(csvCell).join(","), ...rows.map((row) => headers.map((key) => csvCell(row[key])).join(","))].join("\r\n");
    download("profile-refinery-profiles.csv", csv, "text/csv;charset=utf-8");
  });

  document.querySelector("#open-profile-cards").addEventListener("click", () => showProfileCard(0));
  resultList.addEventListener("click", (event) => {
    const button = event.target.closest("[data-profile-card]");
    if (!button) return;
    const sourceIndex = Number(button.dataset.profileCard);
    const sourceResult = latestResponse?.results?.[sourceIndex];
    const profiles = successfulProfiles();
    showProfileCard(profiles.indexOf(sourceResult?.profile));
  });
  document.querySelector("#close-profile-card").addEventListener("click", () => cardDialog.close());
  document.querySelector("#previous-profile-card").addEventListener("click", () => showProfileCard(currentCardIndex - 1));
  document.querySelector("#next-profile-card").addEventListener("click", () => showProfileCard(currentCardIndex + 1));
  document.querySelector("#download-profile-card").addEventListener("click", () => {
    const profile = successfulProfiles()[currentCardIndex];
    if (!profile) return;
    const identity = fieldValue(profile, "identity", {});
    const slug = String(identity?.vanity_slug || "profile").replace(/[^a-z0-9_-]/gi, "-");
    download(`${slug}-profile-card.html`, standaloneCardDocument(profile), "text/html;charset=utf-8");
  });
  document.querySelectorAll("[data-copy-target]").forEach((button) => {
    button.addEventListener("click", async () => {
      const target = document.getElementById(button.dataset.copyTarget);
      if (!target) return;
      const original = button.textContent;
      try {
        await navigator.clipboard.writeText(target.textContent);
        button.textContent = "Copied";
      } catch {
        button.textContent = "Copy failed";
      }
      window.setTimeout(() => { button.textContent = original; }, 1600);
    });
  });
  cardDialog.addEventListener("click", (event) => {
    if (event.target === cardDialog) cardDialog.close();
  });
  cardCanvas.addEventListener("pointermove", (event) => {
    if (matchMedia("(prefers-reduced-motion: reduce)").matches || innerWidth < 700) return;
    const card = cardCanvas.querySelector(".profile-passport");
    if (!card) return;
    const bounds = card.getBoundingClientRect();
    const x = ((event.clientX - bounds.left) / bounds.width - 0.5) * 8;
    const y = ((event.clientY - bounds.top) / bounds.height - 0.5) * -8;
    card.style.setProperty("--tilt-x", `${y.toFixed(2)}deg`);
    card.style.setProperty("--tilt-y", `${x.toFixed(2)}deg`);
  });
  cardCanvas.addEventListener("pointerleave", () => {
    const card = cardCanvas.querySelector(".profile-passport");
    if (!card) return;
    card.style.setProperty("--tilt-x", "0deg");
    card.style.setProperty("--tilt-y", "0deg");
  });
  cardCanvas.addEventListener("error", (event) => {
    const image = event.target.closest("img.passport-avatar");
    if (!image) return;
    image.hidden = true;
    const fallback = image.parentElement?.querySelector(".passport-avatar-fallback");
    fallback?.setAttribute("aria-hidden", "false");
  }, true);

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    formError.hidden = true;
    const urls = profileUrls();
    const invalid = renderUrlValidation();
    if (!urls.length) {
      renderFormError("Enter at least one LinkedIn profile URL.");
      urlsInput.focus();
      return;
    }
    if (urls.length > 10) {
      renderFormError("A single extraction accepts at most 10 profiles.", [`Remove ${urls.length - 10} URL${urls.length - 10 === 1 ? "" : "s"} and try again.`]);
      urlsInput.focus();
      return;
    }
    if (invalid.length) {
      renderFormError("Fix the invalid LinkedIn profile URLs before extraction.", invalid.map((item) => `Line ${item.line}: ${item.error}`));
      urlsInput.focus();
      return;
    }
    if (!form.reportValidity()) return;

    const payload = JSON.stringify({
      urls,
      session: {
        li_at: liAtInput.value,
        jsessionid: jsessionInput.value,
        companion_cookies: companionInput.value || null,
        user_agent: userAgentInput.value,
        accept_language: languageInput.value,
      },
    });

    startProgress(urls.length);
    actionTitle.textContent = "Extraction in progress";
    actionDetail.textContent = `Processing ${urls.length} profile${urls.length === 1 ? "" : "s"} sequentially…`;
    try {
      const responsePromise = fetch("/v1/session-extractions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Request-ID": crypto.randomUUID(),
        },
        cache: "no-store",
        credentials: "same-origin",
        body: payload,
      });
      liAtInput.value = "";
      jsessionInput.value = "";
      companionInput.value = "";
      const response = await responsePromise;
      const contentType = response.headers.get("content-type") || "";
      const data = contentType.includes("json") ? await response.json() : null;
      if (!response.ok) {
        const detail = typeof data?.detail === "string" ? data.detail : data?.title;
        throw new Error(detail || `Request failed with HTTP ${response.status}.`);
      }
      if (!data?.results) throw new Error("The server returned an unexpected response shape.");
      latestResponse = data;
      renderResults(data);
      actionTitle.textContent = "Extraction complete";
      actionDetail.textContent = "Session fields were cleared. Download or review the structured output below.";
    } catch (error) {
      renderFormError("Extraction request failed.", [error instanceof Error ? error.message : "The extraction request failed."]);
      actionTitle.textContent = "Extraction stopped";
      actionDetail.textContent = "Session fields were cleared. Review the error before trying again.";
    } finally {
      stopProgress();
    }
  });

  renderUrlValidation();
})();
