<script lang="ts">
    onMount(() => {
        import('bootstrap')
    })
    
    import { onMount, type Snippet } from 'svelte';
    import type { LayoutData } from './$types';

    let { data, children }: { data: LayoutData, children: Snippet } = $props();
</script>

<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
<!-- -->

<main class="container my-3">
    <a class="h3 mb-2" href="/home">Your Legislative Assistant</a>
    <p class="text-italic small text-muted mb-3">TODO better name - but helps you understand the legislation your representatives are making--and empowers you to respond!</p>

    {@render children()}
</main>

<style>
    :global(.card) {
        font-size: 0.95rem;
    }
    :global(.card-header) {
        padding: 0.5rem 1rem;
    }
    :global(.card-body) {
        padding: 1rem;
    }
    :global(.form-label) {
        margin-bottom: 0.25rem;
    }
    :global(.form-control), :global(.form-select) {
        padding: 0.375rem 0.5rem;
        font-size: 0.95rem;
    }
    :global(.mb-3) {
        margin-bottom: 0.75rem !important;
    }
    :global(.btn) {
        padding: 0.25rem 0.75rem;
    }
    :global(.table td), :global(.table th) {
        padding: 0.5rem;
    }
    :global(.h3) {
        font-size: 1.5rem;
    }
</style>