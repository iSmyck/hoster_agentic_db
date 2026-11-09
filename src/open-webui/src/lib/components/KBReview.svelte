<script lang="ts">
	import { KBClient, KBApiError, type ProposalRecord, type DecisionRecord, type MergeResponse } from '$lib/api/kb.js';

	interface Props {
		proposal?: ProposalRecord;
		actorId?: string;
		onDecision?: (decision: DecisionRecord) => void;
		onMerge?: (result: MergeResponse) => void;
	}

	let { proposal, actorId = '', onDecision, onMerge }: Props = $props();

	let client = $state(new KBClient());
	let loading = $state(false);
	let error = $state('');
	let decision = $state<DecisionRecord | undefined>(undefined);
	let mergeResult = $state<MergeResponse | undefined>(undefined);

	async function handleDecision(action: 'accepted' | 'rejected' | 'cancelled') {
		if (!proposal || !actorId) return;
		loading = true;
		error = '';
		try {
			decision = await client.recordDecision({
				proposal_id: proposal.id,
				action,
				actor_id: actorId,
				idempotency_key: `ui-decision-${proposal.id}-${action}`,
				decision_data: { evidence: { source: 'kb-review-ui' } }
			});
			onDecision?.(decision);
		} catch (err) {
			error = err instanceof KBApiError ? `${err.code}: ${err.message}` : String(err);
		} finally {
			loading = false;
		}
	}

	async function handleMerge() {
		if (!proposal) return;
		loading = true;
		error = '';
		try {
			mergeResult = await client.executeMerge(proposal.id);
			onMerge?.(mergeResult);
		} catch (err) {
			error = err instanceof KBApiError ? `${err.code}: ${err.message}` : String(err);
		} finally {
			loading = false;
		}
	}

	async function handleReconcile() {
		if (!proposal) return;
		loading = true;
		error = '';
		try {
			mergeResult = await client.reconcileMerge(proposal.id);
			onMerge?.(mergeResult);
		} catch (err) {
			error = err instanceof KBApiError ? `${err.code}: ${err.message}` : String(err);
		} finally {
			loading = false;
		}
	}
</script>

<div class="kb-review border rounded-lg p-4 bg-white shadow-sm space-y-4">
	{#if !proposal}
		<p class="text-sm text-gray-500">No proposal selected for review.</p>
	{:else}
		<header class="border-b pb-2">
			<h2 class="text-lg font-semibold">Review Proposal</h2>
			<p class="text-xs text-gray-500 font-mono mt-1">ID: {proposal.id}</p>
			<p class="text-xs text-gray-500 font-mono">Base: {proposal.base_sha.slice(0, 12)}…</p>
			<p class="text-xs text-gray-500 font-mono">Proposal: {proposal.proposal_sha.slice(0, 12)}…</p>
			<p class="text-xs mt-1">
				Status: <span class="font-medium">{proposal.status}</span>
			</p>
		</header>

		{#if error}
			<p class="text-sm text-red-600" role="alert">{error}</p>
		{/if}

		{#if decision}
			<section class="text-sm space-y-1">
				<h3 class="font-semibold">Decision</h3>
				<p>Outcome: <span class="font-medium">{decision.outcome}</span></p>
				<p>State: <span class="font-medium">{decision.state}</span></p>
				<p class="text-xs text-gray-500 font-mono">Hash: {decision.record_sha256.slice(0, 16)}…</p>
				{#if decision.note_id}
					<p class="text-xs text-gray-500">MR Note ID: {decision.note_id}</p>
				{/if}
				<p class="text-xs text-gray-500">Tag: {decision.tag_name}</p>
			</section>
		{/if}

		{#if mergeResult}
			<section class="text-sm space-y-1">
				<h3 class="font-semibold">Merge Result</h3>
				<p>Status: <span class="font-medium">{mergeResult.status}</span></p>
				{#if mergeResult.merge_sha}
					<p class="text-xs text-gray-500 font-mono">Merge SHA: {mergeResult.merge_sha}</p>
				{/if}
				<p class="text-xs text-gray-500">{mergeResult.detail}</p>
				{#if mergeResult.recovery_required}
					<p class="text-xs text-amber-600">Recovery required: target is quarantined.</p>
				{/if}
			</section>
		{/if}

		{#if proposal.status === 'in_review'}
			<section class="flex flex-wrap gap-2">
				<button
					class="px-3 py-1.5 text-sm rounded bg-green-600 text-white hover:bg-green-700 disabled:opacity-50"
					disabled={loading || !actorId}
					on:click={() => handleDecision('accepted')}
				>
					Accept
				</button>
				<button
					class="px-3 py-1.5 text-sm rounded bg-red-600 text-white hover:bg-red-700 disabled:opacity-50"
					disabled={loading || !actorId}
					on:click={() => handleDecision('rejected')}
				>
					Reject
				</button>
				<button
					class="px-3 py-1.5 text-sm rounded bg-gray-500 text-white hover:bg-gray-600 disabled:opacity-50"
					disabled={loading || !actorId}
					on:click={() => handleDecision('cancelled')}
				>
					Cancel
				</button>
			</section>
		{/if}

		{#if decision?.outcome === 'accepted' && decision.state === 'recorded'}
			<section>
				<button
					class="px-3 py-1.5 text-sm rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
					disabled={loading}
					on:click={handleMerge}
				>
					Merge
				</button>
			</section>
		{/if}

		{#if decision?.state === 'quarantined'}
			<section>
				<button
					class="px-3 py-1.5 text-sm rounded bg-amber-600 text-white hover:bg-amber-700 disabled:opacity-50"
					disabled={loading}
					on:click={handleReconcile}
				>
					Reconcile
				</button>
			</section>
		{/if}

		{#if loading}
			<p class="text-sm text-gray-500">Processing…</p>
		{/if}
	{/if}
</div>
