<template>
  <el-empty :description="text" :image-size="72">
    <slot />
  </el-empty>
</template>

<script setup>
defineProps({
  text: { type: String, required: true },
})
</script>