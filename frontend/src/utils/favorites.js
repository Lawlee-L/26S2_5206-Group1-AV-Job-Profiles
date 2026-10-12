const FAVORITES_KEY = "av-job-favorites";

// Get all saved jobs
export function getFavorites() {
    try {
        const savedJobs = localStorage.getItem(FAVORITES_KEY);

        const values = savedJobs ? JSON.parse(savedJobs) : [];
        return Array.isArray(values) ? values.filter(job => job && (job.sourceKey || job.id)) : [];
    } catch (error) {
        console.error("Could not load favorites:", error);
        return [];
    }
}

// Check whether a job is already saved
export function isFavorite(jobId) {
    const favorites = getFavorites();

    return favorites.some(
        (job) => String(job.sourceKey || job.id) === String(jobId)
    );
}

// Save a job
export function saveFavorite(job) {
    const favorites = getFavorites();

    const alreadySaved = favorites.some(
        (item) => String(item.sourceKey || item.id) === String(job.sourceKey || job.id)
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
        (job) => String(job.sourceKey || job.id) !== String(jobId)
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
