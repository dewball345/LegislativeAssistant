<script lang="ts">
    import type { PageData } from './$types';
    import type { StoredData } from '$lib/types';
    import SummaryCard from '$lib/components/SummaryCard.svelte';
    import BillHistoryCard from '$lib/components/BillHistoryCard.svelte';
    import RepresentativesCard from '$lib/components/RepresentativesCard.svelte';
    import DebugJsonCard from '$lib/components/DebugJsonCard.svelte';
    import AnalysisCard from '$lib/components/AnalysisCard.svelte';
    import BenefitsDrawbacksCard from '$lib/components/BenefitsDrawbacksCard.svelte';
    import LetterGeneratorCard from '$lib/components/LetterGeneratorCard.svelte';

    let { data }: { data: PageData } = $props();
    const reportId = $derived(data.id);
    let storedData: StoredData | null = $state(null);
    let userBenefits: any[] = $state([]);
    let userDrawbacks: any[] = $state([]);

    $effect(() => {
        const pastReports = JSON.parse(localStorage.getItem('pastReports') || '[]');
        const report = pastReports.find((r: any) => r.id === reportId);
        if (report) {
            storedData = report.result;
            userBenefits = report.result.user_benefits?.[0]?.records || [];
            userDrawbacks = report.result.user_drawbacks?.[0]?.records || [];
        }
    });
</script>

<div class="container mt-4">
    <h2 class="mb-4 serif-header">Report for "{storedData ? storedData.bill_metadata.bill.title : "Loading"}"</h2>

    {#if storedData?.summaries?.levels}
        <SummaryCard levels={storedData.summaries.levels} />
    {:else}
        <div class="alert alert-info">
            No data found for this report.
        </div>
    {/if}

    {#if storedData?.bill_history}
        <BillHistoryCard history={storedData.bill_history} />
    {/if}

    {#if storedData?.summaries?.rep_profiles}
        <RepresentativesCard profiles={storedData.summaries.rep_profiles} />
    {/if}

    {#if storedData?.pork_barrel_spending?.[0]?.records}
        <AnalysisCard 
            title="Pork Barrel Spending Analysis"
            records={storedData.pork_barrel_spending[0].records}
            explanation="Identifies any extra spending or special projects added to this bill that might benefit specific districts or special interests rather than serving a national purpose."
        />
    {/if}

    {#if storedData?.trojan_horses?.[0]?.records}
        <AnalysisCard 
            title="Trojan Horse Provisions Analysis"
            records={storedData.trojan_horses[0].records}
            explanation="Reveals hidden provisions or unexpected consequences that might be concealed within the bill's complex language."
        />
    {/if}

    {#if storedData?.sleeper_provisions?.[0]?.records}
        <AnalysisCard 
            title="Sleeper Provisions Analysis"
            records={storedData.sleeper_provisions[0].records}
            explanation="Highlights provisions that could have significant future impacts but might not be immediately apparent or take effect at a later date."
        />
    {/if}

    {#if userBenefits.length > 0 || userDrawbacks.length > 0}
        <BenefitsDrawbacksCard benefits={userBenefits} drawbacks={userDrawbacks} />
    {/if}

    {#if storedData}
        <LetterGeneratorCard 
            billTitle={storedData.bill_metadata.bill.title}
            billContext={JSON.stringify(storedData)}
        />
    {/if}

    <!-- {#if storedData}
        <DebugJsonCard data={storedData} />
    {/if} -->
</div>
