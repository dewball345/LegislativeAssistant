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

<div class="min-vh-100 bg-body">
    <nav class="navbar navbar-expand-lg mb-4" style="background-color: #112e51;">
        <div class="container py-2">
            <a class="navbar-brand d-flex align-items-center gap-2" href="/home">
                <i class="bi bi-building-lock fs-4 text-white"></i>
                <h3 class="serif-header text-white" style="font-family: Merriweather, sans-serif;font-weight:900">Your Legislative Assistant</h3>
            </a>
            <p class="text-white-50 mb-0 ms-3 d-none d-md-block small">Empowering informed civic engagement</p>
        </div>
    </nav>

    <div class="container mb-4">
        <div class="alert alert-info border-info small">
            <div class="d-flex align-items-center gap-2">
                <i class="bi bi-robot fs-5"></i>
                <div>
                    <strong>AI-Generated Content Notice:</strong>
                    <p class="mb-0">
                        The analysis, scores, and explanations provided in these reports are generated using AI technology. 
                        While we strive for accuracy, this content should be used as a starting point for your research. 
                        We encourage you to verify specific claims through official government sources and independent research.
                    </p>
                </div>
            </div>
        </div>
    </div>

    <main class="container pb-4">
        {@render children()}
    </main>
</div>

<style>
    @import url('https://fonts.googleapis.com/css2?family=Merriweather:ital,opsz,wght@0,18..144,300..900;1,18..144,300..900&family=Source+Sans+3:ital,wght@0,200..900;1,200..900&display=swap');
    
    :global(.serif-header) {
        font-family: "Merriweather", serif;
        font-optical-sizing: auto;
        /* font-weight: <weight>; */
        font-style: normal;
        font-variation-settings:
            "wdth" 100;
        margin-bottom:-2.1px
    }

    * {
        font-family: "Source Sans 3", sans-serif;
    }
    /* :global(body) {
        font-family: 'League Spartan', system-ui, -apple-system, sans-serif;
    } */

    :global(:root) {
        --gov-primary: #112e51;    /* Deep navy blue used by many .gov sites */
        --gov-primary-dark: #0c1f36;
        --gov-accent: #d83933;     /* Official US red */
        --gov-accent-light: #e87d78;
        --gov-background: #f5f5f0; /* Slightly warm off-white */
        --gov-gray: #4a4a4a;
    }

    :global(body) {
        background-color: var(--gov-background) !important;
    }

    :global(.btn-primary) {
        background-color: var(--gov-primary);
        border-color: var(--gov-primary);
    }

    :global(.btn-primary:hover) {
        background-color: var(--gov-primary-dark);
        border-color: var(--gov-primary-dark);
    }

    :global(.text-primary) {
        color: var(--gov-primary) !important;
    }

    :global(.bg-primary) {
        background-color: var(--gov-primary) !important;
    }

    :global(.card) {
        border: none;
        border-radius: 0.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }

    :global(.badge) {
        font-weight: 500;
        padding: 0.5em 0.85em;
    }

    :global(.accordion-button:not(.collapsed)) {
        background-color: var(--gov-background);
        color: var(--gov-primary);
    }

    :global(.accordion-button:focus) {
        box-shadow: none;
        border-color: var(--gov-primary);
    }

    :global(.btn-link) {
        color: var(--gov-primary);
    }
</style>