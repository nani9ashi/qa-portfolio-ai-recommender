/**
 * 画面制御 / イベントハンドラ
 */
(function () {
  const $ = (id) => document.getElementById(id);

  const screens = {
    input: $("input-screen"),
    loading: $("loading-screen"),
    result: $("result-screen"),
    error: $("error-screen"),
  };

  function showScreen(name) {
    Object.entries(screens).forEach(([k, el]) => {
      el.hidden = (k !== name);
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  // ===== 単元チェックボックス描画 =====
  function renderUnitCheckboxes(containerId, units, otherSelectedIds) {
    const container = $(containerId);
    container.innerHTML = "";
    if (units.length === 0) {
      container.innerHTML = '<p class="hint">学年を選択すると単元が表示されます</p>';
      return;
    }
    units.forEach(u => {
      const label = document.createElement("label");
      label.dataset.unitId = u.id;
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.value = u.id;
      cb.dataset.unitName = u.name;

      // 同じ単元が他方で選択中なら無効化
      if (otherSelectedIds.has(u.id)) {
        cb.disabled = true;
        label.classList.add("disabled");
      }

      label.appendChild(cb);
      label.appendChild(document.createTextNode(`${u.name} (${u.grade})`));
      container.appendChild(label);
    });
  }

  function getCheckedIds(containerId) {
    return Array.from(
      $(containerId).querySelectorAll('input[type="checkbox"]:checked')
    ).map(cb => cb.value);
  }

  function refreshUnitLists() {
    const grade = $("grade").value;
    const units = grade ? getUnitsForGrade(grade) : [];
    const understoodIds = new Set(getCheckedIds("understood-units"));
    const weakIds = new Set(getCheckedIds("weak-units"));
    renderUnitCheckboxes("understood-units", units, weakIds);
    renderUnitCheckboxes("weak-units", units, understoodIds);
    // 再描画後に既存選択を復元
    Array.from($("understood-units").querySelectorAll('input')).forEach(cb => {
      if (understoodIds.has(cb.value)) cb.checked = true;
    });
    Array.from($("weak-units").querySelectorAll('input')).forEach(cb => {
      if (weakIds.has(cb.value)) cb.checked = true;
    });
  }

  // ===== 入力検証 =====
  function validate(grade, understoodIds, weakIds) {
    let ok = true;
    const gradeError = $("grade-error");
    if (!grade) {
      gradeError.textContent = "学年を選択してください。";
      gradeError.hidden = false;
      ok = false;
    } else {
      gradeError.hidden = true;
      gradeError.textContent = "";
    }

    const conflictError = $("conflict-error");
    const conflicts = understoodIds.filter(id => weakIds.includes(id));
    if (conflicts.length > 0) {
      const names = conflicts.map(id => findUnitById(id)?.name).join("・");
      conflictError.textContent = `「${names}」が理解済みと苦手の両方で選択されています。どちらか一方にしてください。`;
      conflictError.hidden = false;
      ok = false;
    } else {
      conflictError.hidden = true;
      conflictError.textContent = "";
    }
    return ok;
  }

  // ===== レコメンド呼び出し (API モック) =====
  function callRecommendApi(input) {
    const forceError = $("force-error").checked;
    const forceSlow = $("force-slow").checked;
    const delay = forceSlow ? 12000 : 600 + Math.random() * 800;

    return new Promise((resolve, reject) => {
      const t0 = performance.now();
      const interval = setInterval(() => {
        const elapsed = ((performance.now() - t0) / 1000).toFixed(1);
        $("loading-elapsed").textContent = `経過時間: ${elapsed}秒`;
      }, 100);
      setTimeout(() => {
        clearInterval(interval);
        if (forceError) {
          reject(new Error("API接続エラー (シミュレート)"));
          return;
        }
        try {
          const result = recommend(input);
          resolve({ result, elapsedMs: performance.now() - t0 });
        } catch (e) {
          reject(e);
        }
      }, delay);
    });
  }

  // ===== 結果描画 =====
  function renderResult({ result, elapsedMs }, input) {
    const container = $("recommendations");
    container.innerHTML = "";

    const meta = $("result-meta");
    meta.textContent = `学年: ${input.grade} / 理解済み: ${input.understoodIds.length}件 / 苦手: ${input.weakIds.length}件 / 応答: ${(elapsedMs/1000).toFixed(2)}秒`;

    if (result.length === 0) {
      const card = document.createElement("div");
      card.className = "rec-card";
      card.innerHTML = `
        <h3>推薦できる単元が見つかりませんでした</h3>
        <p class="reason">理解済み単元と苦手単元の組み合わせから、新たに推薦できる単元が見つかりませんでした。理解済み単元を見直すか、上位の学年に進むことをご検討ください。</p>
      `;
      container.appendChild(card);
      return;
    }

    result.forEach((r, i) => {
      const card = document.createElement("div");
      card.className = "rec-card";
      card.innerHTML = `
        <h3><span class="rank">第${i+1}位</span>${r.unit.name}</h3>
        <p class="reason">${r.reason}</p>
        <p class="meta">学年区分: ${r.unit.grade} / スコア: ${r.score}</p>
      `;
      container.appendChild(card);
    });
  }

  // ===== イベント =====
  $("grade").addEventListener("change", refreshUnitLists);

  $("understood-units").addEventListener("change", refreshUnitLists);
  $("weak-units").addEventListener("change", refreshUnitLists);

  $("recommend-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const grade = $("grade").value;
    const understoodIds = getCheckedIds("understood-units");
    const weakIds = getCheckedIds("weak-units");
    if (!validate(grade, understoodIds, weakIds)) return;

    showScreen("loading");
    try {
      const apiResult = await callRecommendApi({ grade, understoodIds, weakIds });
      renderResult(apiResult, { grade, understoodIds, weakIds });
      showScreen("result");
    } catch (err) {
      $("error-message").textContent =
        `AI APIへの接続に失敗しました（${err.message}）。しばらくしてからもう一度お試しください。`;
      showScreen("error");
    }
  });

  $("retry-btn").addEventListener("click", () => showScreen("input"));
  $("back-btn").addEventListener("click", () => showScreen("input"));
  $("retry-api-btn").addEventListener("click", () => {
    $("recommend-form").requestSubmit();
  });

  // 初期表示
  showScreen("input");
})();
