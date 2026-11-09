CREATE SCHEMA IF NOT EXISTS kb_authz;
CREATE SCHEMA IF NOT EXISTS kb_ops;
CREATE SCHEMA IF NOT EXISTS kb_index;

COMMENT ON SCHEMA kb_authz IS 'Identity, group snapshots, policy bundles, AuthzContext.';
COMMENT ON SCHEMA kb_ops IS 'Git Orchestrator: proposals, decisions, source-sync cursors, cutover records.';
COMMENT ON SCHEMA kb_index IS 'Retrieval: index generations, pointers, query logs.';
