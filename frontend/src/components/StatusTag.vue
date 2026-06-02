<script setup lang="ts">
import { computed } from 'vue'

import { statusLabel, statusType } from '@/utils/display'

const props = defineProps<{ value?: string | null }>()
const tagType = computed(() => statusType(props.value))
const displayText = computed(() => statusLabel(props.value))
</script>

<template>
  <el-tag :type="tagType" effect="plain" round>{{ displayText }}</el-tag>
</template>
