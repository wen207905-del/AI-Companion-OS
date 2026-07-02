<script>
  export let content = ''
  export let streaming = false

  import { parseReplyContent } from '../lib/replyFormat.js'

  $: segments = parseReplyContent(content)
  $: hasSegments = segments.some(s => s.type !== 'narration')

  function paragraphs(text) {
    return String(text || '')
      .split(/\n+/)
      .map(p => p.trim())
      .filter(Boolean)
  }
</script>

<div class="reply-body" class:rich={hasSegments} class:novel={content.length > 400}>
  {#each segments as seg, i (i)}
    {#if seg.type === 'action'}
      <div class="seg-action">
        {#each paragraphs(seg.text) as para}
          <p>{para}</p>
        {/each}
      </div>
    {:else if seg.type === 'speech'}
      <p class="seg-speech">「{seg.text}」</p>
    {:else}
      <div class="seg-narration">
        {#each paragraphs(seg.text) as para}
          <p>{para}</p>
        {/each}
      </div>
    {/if}
  {/each}
  {#if streaming}<span class="stream-cursor">▍</span>{/if}
</div>

<style>
  .reply-body {
    font-size: 0.9rem;
    line-height: 1.85;
    word-break: break-word;
  }

  .reply-body.novel {
    font-size: 0.88rem;
    line-height: 1.9;
  }

  .reply-body.rich {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .seg-action {
    color: #fbbf24;
    font-style: italic;
    font-size: 0.86rem;
    opacity: 0.96;
  }

  .seg-action p,
  .seg-narration p {
    margin: 0 0 8px;
  }

  .seg-action p:last-child,
  .seg-narration p:last-child {
    margin-bottom: 0;
  }

  .seg-speech {
    margin: 0;
    color: #7dd3fc;
    font-weight: 500;
    padding-left: 4px;
    border-left: 2px solid rgba(125, 211, 252, 0.35);
  }

  .seg-narration {
    color: var(--text-primary);
    font-size: 0.88rem;
  }

  .novel .seg-narration {
    text-indent: 0;
  }

  .stream-cursor {
    display: inline-block;
    color: var(--accent-light);
    animation: blink 0.9s step-end infinite;
    margin-left: 1px;
  }

  @keyframes blink {
    50% { opacity: 0; }
  }
</style>
