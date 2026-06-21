// Frontend typeahead UI (Phase 4).

const MIN_PREFIX_LENGTH = 3;
const DEBOUNCE_MS = 300;

const searchInput = document.getElementById("search-input");
const suggestionsList = document.getElementById("suggestions-list");
const searchHint = document.getElementById("search-hint");

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

searchInput.addEventListener("input", () => {
  scheduleFetch(searchInput.value.trim());
});

searchInput.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    clearSuggestions();
    searchHint.textContent = "Type at least 3 characters to see suggestions.";
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

searchInput.addEventListener("blur", () => {
  window.setTimeout(clearSuggestions, 150);
});
