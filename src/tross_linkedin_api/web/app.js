(() => {
  "use strict";

  const form = document.querySelector("#extraction-form");
  const urlsInput = document.querySelector("#profile-urls");
  const apiKeyInput = document.querySelector("#api-key");
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
  let latestResponse = null;

  userAgentInput.value = navigator.userAgent;

  const profileUrls = () => urlsInput.value
    .split(/\r?\n/)
    .map((value) => value.trim())
    .filter(Boolean);

  urlsInput.addEventListener("input", () => {
    urlCount.textContent = `${profileUrls().length} / 10`;
  });

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
      companyName: current?.company_name || "",
      linkedinCompanyUrl: current?.company_url || "",
      linkedinJobTitle: current?.title || "",
      linkedinJobLocation: current?.location || "",
      linkedinJobDescription: current?.description || "",
      previousCompanyName: previous?.company_name || "",
      linkedinPreviousJobTitle: previous?.title || "",
      linkedinSchoolName: school?.school_name || "",
      linkedinSchoolDegree: school?.degree_name || "",
      linkedinSchoolFieldOfStudy: school?.field_of_study || "",
      linkedinSkillsLabel: Array.isArray(skills) ? skills.map((item) => item.name).join(" | ") : "",
      certifications: Array.isArray(certifications) ? certifications.map((item) => item.name).join(" | ") : "",
      languages: Array.isArray(languages) ? languages.map((item) => item.name).join(" | ") : "",
      profileImageUrl: fieldValue(profile, "profile_image", {})?.url || "",
      backgroundImageUrl: fieldValue(profile, "background_image", {})?.url || "",
      refreshedAt: profile?.observed_at || "",
      evidenceMode: profile?.retrieval?.mode || "",
      partial: profile?.partial ?? "",
    };
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
        </div>` : `<div class="error-detail"><strong>${escapeHtml(result.error?.code || "FAILED")}</strong><br>${escapeHtml(result.error?.detail || "No profile data returned.")}</div>`;
      return `<article class="result-card">
        <div class="result-index">${String(index + 1).padStart(2, "0")}</div>
        <div class="result-body">
          <div class="result-topline">
            <div><h3>${escapeHtml(name)}</h3><span class="result-url">${escapeHtml(profile?.canonical_url || result.input_url)}</span></div>
            <span class="result-status ${className}">${escapeHtml(result.status)}</span>
          </div>
          ${facts}
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

  document.querySelector("#download-json").addEventListener("click", () => {
    if (latestResponse) download("tross-profiles.json", JSON.stringify(latestResponse, null, 2), "application/json");
  });
  document.querySelector("#download-csv").addEventListener("click", () => {
    if (!latestResponse) return;
    const rows = latestResponse.results.map(flatten);
    const headers = [...new Set(rows.flatMap((row) => Object.keys(row)))];
    const csv = [headers.map(csvCell).join(","), ...rows.map((row) => headers.map((key) => csvCell(row[key])).join(","))].join("\r\n");
    download("tross-profiles.csv", csv, "text/csv;charset=utf-8");
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    formError.hidden = true;
    const urls = profileUrls();
    if (!urls.length || urls.length > 10) {
      formError.textContent = "Enter between 1 and 10 LinkedIn profile URLs.";
      formError.hidden = false;
      return;
    }
    if (!form.reportValidity()) return;

    const apiKey = apiKeyInput.value;
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

    submitButton.disabled = true;
    actionTitle.textContent = "Extraction in progress";
    actionDetail.textContent = `Processing ${urls.length} profile${urls.length === 1 ? "" : "s"} sequentially…`;
    try {
      const responsePromise = fetch("/v1/session-extractions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": apiKey,
          "X-Request-ID": crypto.randomUUID(),
        },
        cache: "no-store",
        credentials: "same-origin",
        body: payload,
      });
      apiKeyInput.value = "";
      liAtInput.value = "";
      jsessionInput.value = "";
      companionInput.value = "";
      const response = await responsePromise;
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || data.title || `Request failed with HTTP ${response.status}.`);
      latestResponse = data;
      renderResults(data);
      actionTitle.textContent = "Extraction complete";
      actionDetail.textContent = "Session fields were cleared. Download or review the structured output below.";
    } catch (error) {
      formError.textContent = error instanceof Error ? error.message : "The extraction request failed.";
      formError.hidden = false;
      actionTitle.textContent = "Extraction stopped";
      actionDetail.textContent = "Session fields were cleared. Review the error before trying again.";
    } finally {
      submitButton.disabled = false;
    }
  });
})();
