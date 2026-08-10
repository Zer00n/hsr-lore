/**
 * 站点数据类型定义
 * 字段名与 schema/ 下的 JSON Schema 完全一致。
 * 额外字段（_ 前缀）为前端专用，非 schema 定义。
 */

// ── 引证 ────────────────────────────────────────────────────────

export interface Citation {
  cite_id: string;
  quote: string;
  offset_start?: number;
  offset_end?: number;
}

// ── 自然语言声明 ────────────────────────────────────────────────

export type ClaimType = 'fact' | 'interpretation';
export type Confidence = 'attested' | 'inferred' | 'disputed';

export interface NLStatement {
  text: string;
  claim_type: ClaimType;
  confidence: Confidence;
  citations: Citation[];
}

// ── 实体 ────────────────────────────────────────────────────────

export type EntityType = 'AEON' | 'PATH' | 'CHAR' | 'ORGN' | 'PLAC' | 'WRLD' | 'CONC' | 'ARTF' | 'RACE';
export type SourceVolume = 'lore' | 'books' | 'characters' | 'narrative' | 'dialogue' | 'artifacts' | 'rogue';

export interface EntityAttribute {
  key: string;
  value: string;
  claim_type: ClaimType;
  confidence: Confidence;
  citations: Citation[];
}

export interface Entity {
  entity_id: string;
  type: EntityType;
  canonical_name: string;
  aliases: string[];
  summary: NLStatement;
  attributes: EntityAttribute[];
  source_volume: SourceVolume;
  // Frontend-only fields
  _merged: boolean;
  _merge_ids: string[];
  _source_volumes: string[];
}

// ── 关系 ────────────────────────────────────────────────────────

export interface RelationQualifiers {
  native_term?: string;
  status?: string;
  since_event?: string;
  note?: string;
  [key: string]: string | undefined;
}

export interface Relation {
  relation_id: string;
  subject_id: string;
  predicate: string;
  object_id: string;
  qualifiers: RelationQualifiers;
  claim_type: ClaimType;
  confidence: Confidence;
  citations: Citation[];
  source_volume: SourceVolume;
}

// ── 事件 ────────────────────────────────────────────────────────

export type TemporalRelation = 'before' | 'after' | 'during' | 'overlaps' | 'causes' | 'caused_by';

export interface EventRelative {
  relation: TemporalRelation;
  event_id: string;
}

export interface TimelineEvent {
  event_id: string;
  name: string;
  summary: NLStatement;
  participants: string[];
  locations: string[];
  stated_time?: string;
  relative_to: EventRelative[];
  order_hint?: number;
  confidence?: Confidence;
  citations: Citation[];
  source_volume?: string;
  // Frontend-only
  _timeline_inferred: boolean;
}

// ── 矛盾 ────────────────────────────────────────────────────────

export type DiscrepancyKind = 'contradiction' | 'ambiguity' | 'gap' | 'retcon';
export type Impact = 'low' | 'medium' | 'high';

export interface DiscrepancyStatement {
  text: string;
  citation: Citation;
}

export interface Discrepancy {
  discrepancy_id: string;
  kind: DiscrepancyKind;
  topic: string;
  statements: DiscrepancyStatement[];
  analysis: NLStatement & { confidence?: Confidence };
  related_entities: string[];
  impact: Impact;
  // Frontend-only
  _cross_volume: boolean;
}

// ── 归并记录 ────────────────────────────────────────────────────

export type MergeMethod = 'exact_name' | 'alias_match' | 'contextual';

export interface MergeRecord {
  merge_id: string;
  merged_entity_id: string;
  source_entity_ids: string[];
  method: MergeMethod;
  rationale: NLStatement;
  confidence: Confidence;
}

// ── 引证索引条目 ────────────────────────────────────────────────

export interface CitationEntry {
  cite_id: string;
  /** 任务实际引用的原文片段，非语料 clean 全文 */
  quote: string;
  volume: string;
}

// ── 统计数据 ────────────────────────────────────────────────────

export interface Stats {
  citation_pass_rate: number;
  total_calls: number;
  total_input_tokens: number;
  total_output_tokens: number;
  cumulative_afp: number;
  per_task_counts: Record<string, Record<string, number>>;
  rejection_reasons: Record<string, number>;
  totals: {
    entities: number;
    relations: number;
    events: number;
    discrepancies: number;
  };
}
