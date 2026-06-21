// Frontend typeahead UI (Phase 4) + trending panel (Phase 6).

const MIN_PREFIX_LENGTH = 3;
const DEBOUNCE_MS = 300;
const TRENDING_REFRESH_MS = 60_000;

const searchInput = document.getElementById("search-input");
const searchButton = document.getElementById("search-button");
const suggestionsList = document.getElementById("suggestions-list");
const searchHint = document.getElementById("search-hint");
const searchStatus = document.getElementById("search-status");
const trendingList = document.getElementById("trending-list");
const trendingStatus = document.getElementById("trending-status");

let debounceTimer = null;
let activeIndex = -1;
let currentSuggestions = [];
let requestSequence = 0;

function clearSuggestions() {
  currentSuggestions = [];
  activeIndex = -1;
  suggestionsList.innerHTML = "";
  suggestionsList.hidden = true;
  searchInput.setAttribute("aria-expanded", "false");
}

function renderSuggestions(suggestions) {
  currentSuggestions = suggestions;
  activeIndex = -1;
  suggestionsList.innerHTML = "";

  if (suggestions.length === 0) {
    suggestionsList.hidden = true;
    searchInput.setAttribute("aria-expanded", "false");
    return;
  }

  suggestions.forEach((item, index) => {
    const li = document.createElement("li");
    li.id = `suggestion-${index}`;
    li.setAttribute("role", "option");
    li.setAttribute("aria-selected", "false");
    li.dataset.index = String(index);

    const querySpan = document.createElement("span");
    querySpan.className = "suggestion-query";
    querySpan.textContent = item.query;

    const countSpan = document.createElement("span");
    countSpan.className = "suggestion-count";
    countSpan.textContent = String(item.count);

    li.appendChild(querySpan);
    li.appendChild(countSpan);
    li.addEventListener("mousedown", (event) => {
      event.preventDefault();
      selectSuggestion(index);
    });

    suggestionsList.appendChild(li);
  });

  suggestionsList.hidden = false;
  searchInput.setAttribute("aria-expanded", "true");
}

function highlightActiveItem() {
  const items = suggestionsList.querySelectorAll("li");
  items.forEach((item, index) => {
    const selected = index === activeIndex;
    item.setAttribute("aria-selected", selected ? "true" : "false");
  });

  if (activeIndex >= 0 && items[activeIndex]) {
    items[activeIndex].scrollIntoView({ block: "nearest" });
  }
}

function selectSuggestion(index) {
  const suggestion = currentSuggestions[index];
  if (!suggestion) {
    return;
  }

  searchInput.value = suggestion.query;
  clearSuggestions();
  searchHint.textContent = `Selected: ${suggestion.query}`;
}

async function fetchSuggestions(prefix) {
  const sequence = ++requestSequence;
  const response = await fetch(`/suggest?q=${encodeURIComponent(prefix)}`);

  if (!response.ok) {
    throw new Error(`Suggest request failed: ${response.status}`);
  }

  const payload = await response.json();
  if (sequence !== requestSequence) {
    return;
  }

  renderSuggestions(payload.suggestions || []);
}

function scheduleFetch(prefix) {
  if (debounceTimer) {
    clearTimeout(debounceTimer);
  }

  if (prefix.length < MIN_PREFIX_LENGTH) {
    clearSuggestions();
    searchHint.textContent = "Type at least 3 characters to see suggestions.";
    return;
  }

  searchHint.textContent = "Searching...";
  debounceTimer = setTimeout(async () => {
    try {
      await fetchSuggestions(prefix);
      searchHint.textContent =
        currentSuggestions.length > 0
          ? `${currentSuggestions.length} suggestion(s)`
          : "No suggestions found.";
    } catch (error) {
      clearSuggestions();
      searchHint.textContent = "Unable to load suggestions.";
      console.error(error);
    }
  }, DEBOUNCE_MS);
}

async function submitSearch() {
  const query = searchInput.value.trim();
  if (!query) {
    searchStatus.textContent = "Search query cannot be empty.";
    return;
  }

  searchStatus.textContent = "Submitting search...";
  try {
    const response = await fetch("/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });

    if (!response.ok) {
      let detail = `Search failed: ${response.status}`;
      try {
        const payload = await response.json();
        if (typeof payload.detail === "string") {
          detail = payload.detail;
        }
      } catch (_error) {
        // Keep default detail when response body is not JSON.
      }
      throw new Error(detail);
    }

    clearSuggestions();
    searchStatus.textContent = "Search recorded successfully.";
  } catch (error) {
    searchStatus.textContent =
      error instanceof Error ? error.message : "Unable to submit search.";
    console.error(error);
  }
}

searchInput.addEventListener("input", () => {
  scheduleFetch(searchInput.value.replace(/^\s+/, ""));
});

searchInput.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    clearSuggestions();
    searchHint.textContent = "Type at least 3 characters to see suggestions.";
    return;
  }

  if (event.key === "Enter" && activeIndex === -1) {
    event.preventDefault();
    submitSearch();
    return;
  }

  if (currentSuggestions.length === 0) {
    return;
  }

  if (event.key === "ArrowDown") {
    event.preventDefault();
    activeIndex = Math.min(activeIndex + 1, currentSuggestions.length - 1);
    highlightActiveItem();
    return;
  }

  if (event.key === "ArrowUp") {
    event.preventDefault();
    activeIndex = Math.max(activeIndex - 1, 0);
    highlightActiveItem();
    return;
  }

  if (event.key === "Enter") {
    if (activeIndex >= 0) {
      event.preventDefault();
      selectSuggestion(activeIndex);
    }
  }
});

searchButton.addEventListener("click", () => {
  submitSearch();
});

searchInput.addEventListener("blur", () => {
  window.setTimeout(clearSuggestions, 150);
});

function renderTrending(items) {
  trendingList.innerHTML = "";

  if (items.length === 0) {
    trendingStatus.textContent = "No trending searches yet.";
    return;
  }

  trendingStatus.textContent = `${items.length} trending search(es)`;

  items.forEach((item, index) => {
    const li = document.createElement("li");
    li.className = "trending-item";

    const rankSpan = document.createElement("span");
    rankSpan.className = "trending-rank";
    rankSpan.textContent = String(index + 1);

    const querySpan = document.createElement("span");
    querySpan.className = "trending-query";
    querySpan.textContent = item.query;

    const countSpan = document.createElement("span");
    countSpan.className = "trending-count";
    countSpan.textContent = String(item.count);

    li.appendChild(rankSpan);
    li.appendChild(querySpan);
    li.appendChild(countSpan);
    li.addEventListener("click", () => {
      searchInput.value = item.query;
      searchInput.focus();
      scheduleFetch(item.query);
    });

    trendingList.appendChild(li);
  });
}

async function fetchTrending() {
  trendingStatus.textContent = "Loading trending searches...";
  try {
    const response = await fetch("/trending");
    if (!response.ok) {
      throw new Error(`Trending request failed: ${response.status}`);
    }
    const payload = await response.json();
    renderTrending(payload.trending || []);
  } catch (error) {
    trendingStatus.textContent = "Unable to load trending searches.";
    trendingList.innerHTML = "";
    console.error(error);
  }
}

fetchTrending();
window.setInterval(fetchTrending, TRENDING_REFRESH_MS);
