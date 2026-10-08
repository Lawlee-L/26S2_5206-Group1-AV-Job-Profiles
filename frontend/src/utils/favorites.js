const FAVORITES_KEY = "av-job-favorites";

// Get all saved jobs
export function getFavorites() {
    try {
        const savedJobs = localStorage.getItem(FAVORITES_KEY);

        return savedJobs ? JSON.parse(savedJobs) : [];
    } catch (error) {
        console.error("Could not load favorites:", error);
        return [];
    }
}

// Check whether a job is already saved
export function isFavorite(jobId) {
    const favorites = getFavorites();

    return favorites.some(
        (job) => String(job.id) === String(jobId)
    );
}

// Save a job
export function saveFavorite(job) {
    const favorites = getFavorites();

    const alreadySaved = favorites.some(
        (item) => String(item.id) === String(job.id)
    );

    if (!alreadySaved) {
        const updatedFavorites = [...favorites, job];

        localStorage.setItem(
            FAVORITES_KEY,
            JSON.stringify(updatedFavorites)
        );
    }
}

// Remove a saved job
export function removeFavorite(jobId) {
    const favorites = getFavorites();

    const updatedFavorites = favorites.filter(
        (job) => String(job.id) !== String(jobId)
    );

    localStorage.setItem(
        FAVORITES_KEY,
        JSON.stringify(updatedFavorites)
    );
}

// Save if not saved, remove if already saved
export function toggleFavorite(job) {
    if (isFavorite(job.id)) {
        removeFavorite(job.id);
        return false;
    }

    saveFavorite(job);
    return true;
}