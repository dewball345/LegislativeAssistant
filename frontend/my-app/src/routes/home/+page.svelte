<script lang="ts">
    import { onMount } from "svelte";
    import type { PageData } from "./$types";
    import { goto } from "$app/navigation";

    let { data }: { data: PageData } = $props();
    let isEditing = $state(false);

    // Load profile from localStorage on initialization
    let profile = $state({
        name: "",
        gender: "",
        profession: "",
        location: "",
        politicalInterests: [] as string[],
        additionalInfo: "",
    });

    let pastReports: any[] = $state([]);
    $inspect(pastReports)

    onMount(() => {
        let savedProfile = window.localStorage.getItem("userProfile");
        if (savedProfile) {
            profile = JSON.parse(savedProfile);
        }

        // Load past reports from localStorage
        try {
            const savedReports = localStorage.getItem('pastReports');
            if (savedReports) {
                pastReports = JSON.parse(savedReports);
                // Sort reports by date, most recent first
                pastReports.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
            }
        } catch (error) {
            console.error("Error loading past reports:", error);
        }
    });

    async function handleProfileAction() {
        if (isEditing) {
            await saveProfile();
        }
        isEditing = !isEditing;
    }

    async function saveProfile() {
        try {
            localStorage.setItem("userProfile", JSON.stringify(profile));
            console.log("Profile saved successfully");
        } catch (error) {
            console.error("Error saving profile:", error);
            // TODO: Show error message to user
        }
    }

    function handleInterestChange(categoryId: string, checked: boolean) {
        if (checked) {
            if (profile.politicalInterests.length < 3) {
                profile.politicalInterests = [
                    ...profile.politicalInterests,
                    categoryId,
                ];
            }
        } else {
            profile.politicalInterests = profile.politicalInterests.filter(
                (id) => id !== categoryId
            );
        }
    }

    const interestCategories = [
        { id: "healthcare", label: "Healthcare" },
        { id: "education", label: "Education" },
        { id: "environment", label: "Environment" },
        { id: "economy", label: "Economy" },
        { id: "national-security", label: "National Security" },
        { id: "social-justice", label: "Social Justice" },
    ];

    let billDetails = $state({
        congress: "",
        type: "",
        number: "",
    });

    async function callWorkflow() {
        try {
            const workflowData = {
                profile: JSON.stringify(profile),
                congress_num: billDetails.congress,
                type: billDetails.type,
                bill_num: billDetails.number,
            };

            const response = await fetch(
                "http://localhost:8000/call_workflow",
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify(workflowData),
                }
            );
            const data = await response.json();

            const result = data.result
            // Get existing reports from localStorage
            let existingReports = JSON.parse(localStorage.getItem('pastReports') || '[]');
            
            let currentId = crypto.randomUUID()
            // Create new report object with unique ID
            const newReport = {
                id: currentId,
                billId: `${billDetails.type}${billDetails.number}`,
                date: new Date().toISOString().split('T')[0],
                title: result.title || 'Bill Analysis',
                result: result
            };

            // Add new report to existing reports
            existingReports.push(newReport);

            // Save back to localStorage
            localStorage.setItem('pastReports', JSON.stringify(existingReports));

            // Update the pastReports state so the UI updates immediately
            pastReports = existingReports;

            goto(`/report/${currentId}`)
        } catch (error) {
            console.error("Error:", error);
        }
    }

    let status: 'idle' | 'loading' = $state('idle')
    

    async function handleGenerateReport() {
        status = 'loading'
        await callWorkflow()
        status = 'idle'
    }

    let recommendedBills = [
        { id: "HR1234", title: "Climate Change Act 2025" },
        { id: "S789", title: "Healthcare Reform Bill" },
        { id: "HR456", title: "Education Funding Act" },
    ];
</script>

{#if status === 'loading'}
    <h1>Loading....</h1>
{:else}
    <div class="row g-3">
        <!-- Profile Section -->
        <div class="col-md-6">
            <div class="card">
                <div class="card-body">
                    <div
                        class="d-flex justify-content-between align-items-center mb-3"
                    >
                        <h4 class="mb-0">Your Profile</h4>
                        <button
                            class="btn btn-{isEditing
                                ? 'primary'
                                : 'secondary'} btn-sm"
                            onclick={handleProfileAction}
                        >
                            {isEditing ? "Save Profile" : "Edit Profile"}
                        </button>
                    </div>
                    <div class="row g-2">
                        <div class="col-12">
                            <div class="row g-2">
                                <div class="col-4">
                                    <label for="name" class="form-label small"
                                        >Name</label
                                    >
                                    <input
                                        type="text"
                                        id="name"
                                        class="form-control form-control-sm"
                                        bind:value={profile.name}
                                        disabled={!isEditing}
                                    />
                                </div>
                                <div class="col-4">
                                    <label for="gender" class="form-label small"
                                        >Gender</label
                                    >
                                    <input
                                        type="text"
                                        id="gender"
                                        class="form-control form-control-sm"
                                        bind:value={profile.gender}
                                        disabled={!isEditing}
                                    />
                                </div>
                                <div class="col-4">
                                    <label for="profession" class="form-label small"
                                        >Profession</label
                                    >
                                    <input
                                        type="text"
                                        id="profession"
                                        class="form-control form-control-sm"
                                        bind:value={profile.profession}
                                        disabled={!isEditing}
                                    />
                                </div>
                            </div>
                        </div>
                        <div class="col-12">
                            <label for="location" class="form-label small"
                                >Location (City, State ZIP)</label
                            >
                            <input
                                type="text"
                                id="location"
                                class="form-control form-control-sm"
                                placeholder="e.g., Austin, TX 78701"
                                bind:value={profile.location}
                                disabled={!isEditing}
                            />
                        </div>
                        <div class="col-12">
                            <label class="form-label small">Top Priorities</label>
                            <div class="row g-2">
                                {#each interestCategories as category}
                                    <div class="col-6">
                                        <div class="form-check">
                                            <input
                                                class="form-check-input"
                                                type="checkbox"
                                                id={category.id}
                                                checked={profile.politicalInterests.includes(
                                                    category.id
                                                )}
                                                disabled={!isEditing}
                                                onchange={(e) =>
                                                    handleInterestChange(
                                                        category.id,
                                                        e.currentTarget.checked
                                                    )}
                                            />
                                            <label
                                                class="form-check-label"
                                                for={category.id}
                                            >
                                                {category.label}
                                            </label>
                                        </div>
                                    </div>
                                {/each}
                            </div>
                        </div>
                        <div class="col-12">
                            <label class="form-label small"
                                >Additional Information</label
                            >
                            <textarea
                                class="form-control form-control-sm"
                                rows="2"
                                bind:value={profile.additionalInfo}
                                disabled={!isEditing}
                            ></textarea>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Generate Report Section -->
        <div class="col-md-6">
            <div class="card">
                <div class="card-body">
                    <h4 class="mb-1">Generate Report</h4>
                    <div class="mb-3">
                        <label class="h6 form-label mt-2">Enter Bill Code...</label>
                        <div class="row g-2">
                            <div class="col-3">
                                <input
                                    type="text"
                                    class="form-control form-control-sm"
                                    placeholder="Congress #"
                                    bind:value={billDetails.congress}
                                />
                            </div>
                            <div class="col-4">
                                <input
                                    type="text"
                                    class="form-control form-control-sm"
                                    placeholder="Type (HR, S)"
                                    bind:value={billDetails.type}
                                />
                            </div>
                            <div class="col-5">
                                <div class="d-flex gap-2">
                                    <input
                                        type="text"
                                        class="form-control form-control-sm"
                                        placeholder="Bill #"
                                        bind:value={billDetails.number}
                                    />
                                    <button
                                        class="btn btn-primary btn-sm"
                                        onclick={handleGenerateReport}
                                        >GENERATE</button
                                    >
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="mt-3">
                        <h4 class="h6 mb-2">...or try Recommended Bills</h4>
                        <div class="row g-2">
                            {#each recommendedBills as bill}
                                <div class="col">
                                    <div class="card h-100">
                                        <div class="card-body p-2">
                                            <div class="d-flex flex-column">
                                                <span class="fw-medium small"
                                                    >{bill.id}</span
                                                >
                                                <small class="text-muted"
                                                    >{bill.title}</small
                                                >
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            {/each}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Past Reports Section -->
    <div class="row mt-4">
        <div class="col-12">
            <h1 class="h3 mb-3">Past Reports</h1>
            <div class="row g-3">
                {#if pastReports.length > 0}
                    {#each pastReports as report}
                        <div class="col-md-6 col-lg-3">
                            <div class="card h-100">
                                <div class="card-body p-3">
                                    <div
                                        class="d-flex justify-content-between align-items-start"
                                    >
                                        <div>
                                            <h5 class="h6 mb-1">{report.result.bill_metadata.bill.title}</h5>
                                            <div class="text-muted small">
                                                <div>{report.billId}</div>
                                                <div>{report.date}</div>
                                            </div>
                                        </div>
                                        <a
                                            href="/report/{report.id}"
                                            class="btn btn-outline-primary btn-sm"
                                            >View</a
                                        >
                                    </div>
                                </div>
                            </div>
                        </div>
                    {/each}
                {:else}
                    <p class="">No past reports to show</p>
                {/if}
            </div>
        </div>
    </div>
{/if}