<script lang="ts">
    onMount(() => {
        import('bootstrap')
    })
    
    import { onMount, type Snippet } from 'svelte';
    import type { LayoutData } from './$types';

    let { data, children }: { data: LayoutData, children: Snippet } = $props();
</script>

<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">

<div class="min-vh-100 bg-light">
    <nav class="navbar navbar-expand-lg bg-white shadow-sm mb-4">
        <div class="container py-2">
            <a class="navbar-brand d-flex align-items-center gap-2" href="/home">
                <i class="bi bi-building-lock text-primary fs-4"></i>
                <span class="fw-semibold">Your Legislative Assistant</span>
            </a>
            <p class="text-muted mb-0 ms-3 d-none d-md-block small">Empowering informed civic engagement</p>
        </div>
    </nav>

    <main class="container pb-4">
        {@render children()}
    </main>
</div>

<style>
    :global(body) {
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }

    :global(.card) {
        border: none;
        border-radius: 0.75rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }

    :global(.badge) {
        font-weight: 500;
        padding: 0.5em 0.85em;
    }

    :global(.accordion-button:not(.collapsed)) {
        background-color: var(--bs-primary-bg-subtle);
        color: var(--bs-primary);
    }

    :global(.accordion-button:focus) {
        box-shadow: none;
        border-color: var(--bs-border-color);
    }
</style>